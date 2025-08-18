"""
Conversation management for the Discord LLM Bot.

This module orchestrates conversation flow, manages context, handles
LLM interactions, and maintains conversation state across Discord
interactions. It serves as the central coordination point between
the Discord bot, LLM client, and database.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from discord_llm_bot.config import ConversationConfig, AppConfig
from discord_llm_bot.utils.logging import (
    get_logger, 
    log_function_call, 
    log_conversation_event,
    log_operation_timing,
)
from discord_llm_bot.utils.exceptions import ConversationError, LLMAPIError
from discord_llm_bot.llm.client import LLMClient
from discord_llm_bot.llm.models import ChatMessage, MessageRole
from discord_llm_bot.database.repositories import DatabaseManager
from discord_llm_bot.database.models import User, Conversation, Message
from discord_llm_bot.conversation.memory import MemoryManager
from discord_llm_bot.rag.integration import RAGIntegration
from discord_llm_bot.privacy.manager import PrivacyManager, RetentionPolicy


class ConversationManager:
    """
    Central manager for conversation flow and state.
    
    This class coordinates all aspects of conversation management,
    including message routing, context preparation, LLM interaction,
    and state persistence. It provides a high-level interface for
    the Discord bot to manage conversations.
    
    Key Features:
    - Conversation lifecycle management
    - Context window optimization
    - LLM interaction coordination  
    - Conversation history persistence
    - Multi-user conversation support
    - Automatic cleanup and maintenance
    
    Attributes:
        config: Conversation configuration
        llm_client: LLM API client
        db_manager: Database manager
        memory_manager: Memory and context manager
    """
    
    def __init__(
        self,
        config: AppConfig,
        llm_client: LLMClient,
        db_manager: DatabaseManager,
    ) -> None:
        """
        Initialize the conversation manager.
        
        Args:
            config: Full application configuration
            llm_client: LLM API client
            db_manager: Database manager
        """
        self.config = config.conversation
        self.llm_client = llm_client
        self.db_manager = db_manager
        self.memory_manager = MemoryManager(config.conversation)
        self.logger = get_logger(__name__)
        
        # Initialize privacy manager
        privacy_policy = RetentionPolicy(
            operational_days=7,
            training_days=30,
            user_consent_required=True,
            auto_cleanup_enabled=True
        )
        # Extract database file path from the database URL
        db_path = self.db_manager.config.url.replace("sqlite:///", "").replace("./", "")
        self.privacy_manager = PrivacyManager(db_path, privacy_policy)
        
        # Initialize RAG integration
        self.rag_integration = RAGIntegration(config.rag)
        
        # Use system prompt from config (file or direct) or fallback to default
        self.default_system_prompt = config.llm.get_system_prompt() or (
            "You are a helpful AI assistant in a Discord server. "
            "You can engage in natural conversations, answer questions, "
            "help with various tasks, and provide information. "
            "Be friendly, concise, and helpful. "
            "If you're unsure about something, say so rather than guessing."
        )
        
        log_function_call("ConversationManager.__init__")
    
    async def get_or_create_conversation(
        self,
        user_id: int,
        channel_id: int,
        guild_id: Optional[int] = None,
    ) -> int:
        """
        Get or create a conversation for the given context.
        
        Uses hybrid conversation model:
        - Shared context channel: All users share the same conversation
        - DMs and other channels: Individual conversations per user
        
        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID
            guild_id: Discord guild ID (None for DMs)
            
        Returns:
            Conversation ID
            
        Raises:
            ConversationError: If conversation cannot be created
        """
        log_function_call(
            "get_or_create_conversation",
            user_id=user_id,
            channel_id=channel_id,
            guild_id=guild_id,
        )
        
        try:
            # Determine if this is a shared context channel
            is_shared_context = (
                self.config.shared_context_channel_id is not None and
                channel_id == self.config.shared_context_channel_id
            )
            
            if is_shared_context:
                # Shared context: use a shared "user" for the channel
                # Create a special shared user for this channel
                shared_user = await self.db_manager.get_or_create_user(
                    discord_id=999999999999999999,  # Special ID for shared context
                    username=f"SharedContext_{channel_id}",
                )
                
                # Get or create shared conversation
                conversation = await self.db_manager.get_or_create_conversation(
                    user_id=shared_user.id,
                    channel_id=channel_id,
                    guild_id=guild_id,
                )
                
                self.logger.info(
                    "Using shared context conversation",
                    conversation_id=conversation.id,
                    channel_id=channel_id,
                    requesting_user_id=user_id,
                )
            else:
                # Private context: individual conversation per user
                user = await self.db_manager.get_or_create_user(
                    discord_id=user_id,
                    username=f"User_{user_id}",  # Will be updated with real username later
                )
                
                # Get or create individual conversation
                conversation = await self.db_manager.get_or_create_conversation(
                    user_id=user.id,
                    channel_id=channel_id,
                    guild_id=guild_id,
                )
                
                self.logger.info(
                    "Using private context conversation",
                    conversation_id=conversation.id,
                    user_id=user_id,
                    channel_id=channel_id,
                )
            
            return conversation.id
            
        except Exception as e:
            raise ConversationError(
                "Failed to get or create conversation",
                context={
                    "user_id": user_id,
                    "channel_id": channel_id,
                    "guild_id": guild_id,
                },
                original_error=e,
            )
    
    async def add_message(
        self,
        conversation_id: int,
        content: str,
        role: str,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: Conversation ID
            content: Message content
            role: Message role (user, assistant, system)
            extra_data: Optional metadata
            
        Returns:
            Created message
            
        Raises:
            ConversationError: If message cannot be added
        """
        log_function_call(
            "add_message",
            conversation_id=conversation_id,
            role=role,
            content_length=len(content),
        )
        
        try:
            # Get user ID from conversation
            async with self.db_manager.get_session() as session:
                from sqlalchemy import select
                stmt = select(Conversation).where(Conversation.id == conversation_id)
                result = await session.execute(stmt)
                conversation = result.scalar_one_or_none()
                
                if not conversation:
                    raise ConversationError(f"Conversation {conversation_id} not found")
                
                user_id = conversation.user_id
            
            # Check privacy consent for user messages
            if role == "user" and not self.privacy_manager.should_store_message(user_id):
                self.logger.info(f"Skipping message storage for user {user_id} - no consent")
                # Return a mock message that won't be persisted
                from datetime import datetime
                return Message(
                    id=-1,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    role=role,
                    content="[NOT STORED - NO CONSENT]",
                    created_at=datetime.now(),
                    token_count=0,
                    extra_data=extra_data or {},
                    is_deleted=True
                )
            
            # Count tokens for the message
            chat_msg = ChatMessage(role=MessageRole(role), content=content)
            token_count = self.memory_manager.count_message_tokens(chat_msg)
            
            # Add message to database
            message = await self.db_manager.add_message(
                conversation_id=conversation_id,
                user_id=user_id,
                role=role,
                content=content,
                token_count=token_count,
                extra_data=extra_data,
            )
            
            return message
            
        except Exception as e:
            raise ConversationError(
                "Failed to add message to conversation",
                context={
                    "conversation_id": conversation_id,
                    "role": role,
                    "content_length": len(content),
                },
                original_error=e,
            )
    
    async def generate_response(
        self,
        conversation_id: int,
        system_prompt: Optional[str] = None,
        current_user_name: Optional[str] = None,
    ) -> str:
        """
        Generate an LLM response for a conversation.
        
        Args:
            conversation_id: Conversation ID
            system_prompt: Optional custom system prompt
            current_user_name: Username of the person who just sent the message we're responding to
            
        Returns:
            Generated response text
            
        Raises:
            ConversationError: If response generation fails
            LLMAPIError: If LLM API call fails
        """
        log_function_call("generate_response", conversation_id=conversation_id)
        
        try:
            with log_operation_timing(
                "generate_response",
                conversation_id=conversation_id,
            ) as correlation_id:
                
                # Get conversation messages
                with log_operation_timing(
                    "fetch_conversation_messages",
                    conversation_id=conversation_id,
                    correlation_id=correlation_id,
                ):
                    messages = await self.db_manager.get_conversation_messages(
                        conversation_id=conversation_id,
                        limit=self.config.max_history,
                    )
                
                # DEBUG: Log message count and content overview
                self.logger.info(f"Found {len(messages)} messages in conversation {conversation_id}")
                for i, msg in enumerate(messages[-3:]):  # Show last 3 messages
                    self.logger.info(f"Message {i}: role={msg.role}, content={msg.content[:100]}...")
                
                if not messages:
                    # No conversation history, use a default greeting
                    log_conversation_event(
                        "new_conversation_greeting",
                        conversation_id=conversation_id,
                        user_id=0,  # Unknown at this point
                        correlation_id=correlation_id,
                    )
                    return "Hello! How can I help you today?"
                
                # Prepare context with memory management
                prompt = system_prompt or self.default_system_prompt
                
                # Check if we should enhance with RAG
                last_user_message = ""
                conversation_context = ""
                
                # Get the last few messages for context
                recent_messages = messages[-5:] if len(messages) > 5 else messages
                for msg in recent_messages:
                    # Extract username from extra_data if available - prefer display name
                    username = "User"
                    if hasattr(msg, 'extra_data') and msg.extra_data:
                        if isinstance(msg.extra_data, dict):
                            # Try display name first, fall back to username
                            username = msg.extra_data.get('discord_display_name', 
                                                        msg.extra_data.get('discord_username', 'User'))
                        else:
                            # Handle case where extra_data might be a JSON string
                            try:
                                import json
                                extra_data = json.loads(msg.extra_data) if isinstance(msg.extra_data, str) else msg.extra_data
                                # Try display name first, fall back to username
                                username = extra_data.get('discord_display_name', 
                                                        extra_data.get('discord_username', 'User'))
                            except (json.JSONDecodeError, TypeError):
                                username = "User"
                    
                    if msg.role == "user":
                        conversation_context += f"{username}: {msg.content}\n"
                    elif msg.role == "assistant":
                        # Skip very long assistant responses that look like generic lists
                        if len(msg.content) > 500 and ("Injuries" in msg.content or "recommendations" in msg.content):
                            conversation_context += f"sci-assist: [provided sports recommendations]\n"
                        else:
                            conversation_context += f"sci-assist: {msg.content}\n"
                
                # DEBUG: Log what conversation context we're seeing
                if conversation_context.strip():
                    self.logger.info(f"Conversation context being used:\n{conversation_context}")
                else:
                    self.logger.info("No conversation context found - this may be the first message")
                
                # Get the most recent user message for RAG triggering
                for msg in reversed(messages):
                    if msg.role == "user":
                        last_user_message = msg.content
                        break
                
                # Get the current user's name from the most recent message or parameter
                current_responding_to_user = current_user_name
                self.logger.info(f"DEBUG: current_user_name parameter = '{current_user_name}'")
                
                if not current_responding_to_user and messages:
                    # Fallback: extract from the most recent user message
                    last_msg = messages[-1]
                    if last_msg.role == "user" and hasattr(last_msg, 'extra_data') and last_msg.extra_data:
                        if isinstance(last_msg.extra_data, dict):
                            # Try display name first, fall back to username
                            current_responding_to_user = last_msg.extra_data.get('discord_display_name', 
                                                               last_msg.extra_data.get('discord_username', 'User'))
                        else:
                            try:
                                import json
                                extra_data = json.loads(last_msg.extra_data) if isinstance(last_msg.extra_data, str) else last_msg.extra_data
                                # Try display name first, fall back to username
                                current_responding_to_user = extra_data.get('discord_display_name', 
                                                                   extra_data.get('discord_username', 'User'))
                            except (json.JSONDecodeError, TypeError):
                                current_responding_to_user = "User"
                
                self.logger.info(f"DEBUG: Final current_responding_to_user = '{current_responding_to_user}'")
                
                # Try to enhance with RAG if appropriate
                rag_enhanced = False
                if last_user_message and self.rag_integration.should_use_rag(last_user_message):
                    self.logger.info(f"Attempting RAG enhancement for query: {last_user_message[:100]}...")
                    
                    try:
                        rag_result = await self.rag_integration.enhance_response(last_user_message)
                        if rag_result:
                            rag_context, sources = rag_result
                            
                            # Enhance the system prompt with RAG context while preserving conversation flow
                            enhanced_prompt = self.rag_integration.format_enhanced_prompt(
                                original_query=last_user_message,
                                user_context=prompt + f"\n\nRECENT CONVERSATION CONTEXT (important for understanding the query - reference users by name):\n{conversation_context}",
                                rag_context=rag_context,
                                sources=sources
                            )
                            enhanced_prompt += f"\nIMPORTANT: Keep response SHORT (2-3 sentences max) and reference specific users from the conversation.\n"
                            if current_responding_to_user:
                                enhanced_prompt += f"\nYou are responding to {current_responding_to_user}'s message.\n"
                            
                            prompt = enhanced_prompt
                            rag_enhanced = True
                            
                            self.logger.info(f"RAG enhancement successful, enhanced prompt length: {len(prompt)}")
                            self.logger.debug(f"Final enhanced prompt being sent to LLM:\n{prompt[:500]}...")
                        else:
                            self.logger.debug("RAG enhancement returned empty result")
                    except Exception as e:
                        self.logger.warning(f"RAG enhancement failed: {e}")
                else:
                    # Even without RAG, include conversation context
                    if conversation_context.strip():
                        # Make the conversation flow more explicit
                        context_header = "\n\nRECENT CONVERSATION CONTEXT (respond based on this discussion and reference users by name):\n"
                        prompt = prompt + context_header + conversation_context
                        
                        # If the last user message is vague but conversation has clear context, note this
                        if last_user_message and len(last_user_message.split()) <= 10:  # Short/vague message
                            prompt += f"\nNOTE: '{last_user_message}' was asked right after this discussion - respond based on the conversation topic, not as a standalone question.\n"
                            prompt += f"IMPORTANT: Keep your response SHORT (2-3 sentences max) and reference the specific user who mentioned the relevant topic.\n"
                        
                        # Always add information about who we're responding to
                        if current_responding_to_user:
                            prompt += f"\nYou are responding to {current_responding_to_user}'s message.\n"
                    
                    self.logger.debug(f"No RAG enhancement - using standard prompt with conversation context")
                    # DEBUG: Log the full prompt being sent
                    self.logger.info(f"Standard prompt being sent to LLM (first 1000 chars):\n{prompt[:1000]}...")
                
                with log_operation_timing(
                    "prepare_context",
                    conversation_id=conversation_id,
                    message_count=len(messages),
                    correlation_id=correlation_id,
                ):
                    chat_messages, total_tokens = self.memory_manager.prepare_context(
                        messages=messages,
                        system_prompt=prompt,
                    )
                
                log_conversation_event(
                    "context_prepared",
                    conversation_id=conversation_id,
                    user_id=messages[0].user_id if messages else 0,
                    correlation_id=correlation_id,
                    message_count=len(chat_messages),
                    total_tokens=total_tokens,
                    context_window_usage=f"{total_tokens}/{self.memory_manager.config.context_window_tokens}",
                    rag_enhanced=rag_enhanced,
                )
                
                self.logger.debug(
                    "Prepared context for LLM",
                    conversation_id=conversation_id,
                    message_count=len(chat_messages),
                    total_tokens=total_tokens,
                    correlation_id=correlation_id,
                )
                
                # Generate response from LLM
                with log_operation_timing(
                    "llm_generate_completion",
                    conversation_id=conversation_id,
                    correlation_id=correlation_id,
                ):
                    response = await self.llm_client.generate_chat_completion(
                        messages=chat_messages,
                    )
                
                log_conversation_event(
                    "response_generated",
                    conversation_id=conversation_id,
                    user_id=messages[0].user_id if messages else 0,
                    correlation_id=correlation_id,
                    response_length=len(response.content),
                    tokens_used=response.usage.total_tokens if response.usage else None,
                    finish_reason=response.choices[0].finish_reason if response.choices else None,
                )
                
                self.logger.debug(
                    "Generated LLM response",
                    conversation_id=conversation_id,
                    response_length=len(response.content),
                    tokens_used=response.usage.total_tokens if response.usage else None,
                    correlation_id=correlation_id,
                )
                
                # Optionally add follow-up question to encourage discussion
                enhanced_response = self._maybe_add_followup_question(
                    response.content, 
                    messages
                )
                
                return enhanced_response
            
        except LLMAPIError:
            # Re-raise LLM API errors as-is
            raise
        except Exception as e:
            raise ConversationError(
                "Failed to generate response",
                context={"conversation_id": conversation_id},
                original_error=e,
            )
    
    async def reset_conversation(
        self,
        user_id: int,
        channel_id: int,
        guild_id: Optional[int] = None,
    ) -> None:
        """
        Reset a conversation by clearing its history.
        
        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID
            guild_id: Discord guild ID
            
        Raises:
            ConversationError: If conversation cannot be reset
        """
        log_function_call(
            "reset_conversation",
            user_id=user_id,
            channel_id=channel_id,
            guild_id=guild_id,
        )
        
        try:
            # Find the conversation
            conversation_id = await self.get_or_create_conversation(
                user_id=user_id,
                channel_id=channel_id,
                guild_id=guild_id,
            )
            
            # Reset it
            await self.db_manager.reset_conversation(conversation_id)
            
            self.logger.debug("Reset conversation", conversation_id=conversation_id)
            
        except Exception as e:
            raise ConversationError(
                "Failed to reset conversation",
                context={
                    "user_id": user_id,
                    "channel_id": channel_id,
                    "guild_id": guild_id,
                },
                original_error=e,
            )
    
    async def get_conversation_context(
        self,
        user_id: int,
        channel_id: int,
        guild_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get conversation context and statistics.
        
        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID
            guild_id: Discord guild ID
            
        Returns:
            Dictionary with conversation context info, or None if no conversation
        """
        try:
            # Find the conversation
            conversation_id = await self.get_or_create_conversation(
                user_id=user_id,
                channel_id=channel_id,
                guild_id=guild_id,
            )
            
            # Get conversation stats
            stats = await self.db_manager.get_conversation_stats(conversation_id)
            
            # Get recent messages for context calculation
            messages = await self.db_manager.get_conversation_messages(
                conversation_id=conversation_id,
                limit=self.config.max_history,
            )
            
            # Calculate context tokens
            if messages:
                chat_messages, context_tokens = self.memory_manager.prepare_context(
                    messages=messages,
                    system_prompt=self.default_system_prompt,
                )
            else:
                context_tokens = 0
            
            return {
                "conversation_id": conversation_id,
                "message_count": stats["message_count"],
                "total_tokens": stats["total_tokens"],
                "context_tokens": context_tokens,
                "created_at": stats["created_at"],
                "updated_at": stats["updated_at"],
                "last_message": stats["last_message"],
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get conversation context",
                error=str(e),
                user_id=user_id,
                channel_id=channel_id,
            )
            return None
    
    async def cleanup_old_conversations(self) -> int:
        """
        Clean up old conversations based on configuration.
        
        Returns:
            Number of conversations cleaned up
        """
        log_function_call("cleanup_old_conversations")
        
        try:
            count = await self.db_manager.cleanup_old_conversations(
                days=self.config.auto_cleanup_days
            )
            
            self.logger.info("Cleaned up old conversations", count=count)
            return count
            
        except Exception as e:
            self.logger.error("Failed to cleanup old conversations", error=str(e))
            return 0
    
    async def get_conversation_summary(
        self,
        conversation_id: int,
    ) -> Dict[str, Any]:
        """
        Get a summary of a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Dictionary with conversation summary
        """
        try:
            # Get conversation stats
            stats = await self.db_manager.get_conversation_stats(conversation_id)
            
            # Get recent messages
            messages = await self.db_manager.get_conversation_messages(
                conversation_id=conversation_id,
                limit=10,  # Last 10 messages for summary
            )
            
            # Calculate some basic metrics
            user_messages = [m for m in messages if m.role == "user"]
            assistant_messages = [m for m in messages if m.role == "assistant"]
            
            return {
                "conversation_id": conversation_id,
                "total_messages": stats["message_count"],
                "user_messages": len(user_messages),
                "assistant_messages": len(assistant_messages),
                "total_tokens": stats["total_tokens"],
                "created_at": stats["created_at"],
                "last_activity": stats["last_message"],
                "is_active": stats["last_message"] and (
                    datetime.utcnow() - stats["last_message"]
                ).days < 1,
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get conversation summary",
                error=str(e),
                conversation_id=conversation_id,
            )
            return {
                "conversation_id": conversation_id,
                "error": str(e),
            }
    
    def _maybe_add_followup_question(self, response: str, messages: List[Message]) -> str:
        """
        Optionally add a follow-up question to encourage discussion.
        
        Args:
            response: The original LLM response
            messages: Recent conversation messages for context
            
        Returns:
            Enhanced response with optional follow-up question
        """
        # Don't add questions if response is very long
        if len(response) > 800:
            return response
            
        # Don't add if there's already a question mark
        if '?' in response:
            return response
            
        # Skip for emergency/medical advice responses
        emergency_keywords = ['emergency', 'doctor', 'medical attention', 'call 911', 'urgent']
        if any(keyword in response.lower() for keyword in emergency_keywords):
            return response
            
        # Get the last user message to understand context
        user_messages = [m for m in messages if m.role == "user"]
        if not user_messages:
            return response
            
        last_message = user_messages[-1].content.lower()
        
        # Topic-based follow-up questions
        follow_up = None
        
        if any(word in last_message for word in ['transfer', 'moving', 'getting up', 'getting out']):
            follow_up = "What transfer techniques have worked best for others here?"
        elif any(word in last_message for word in ['wheelchair', 'chair', 'wheels']):
            follow_up = "Anyone have experience with similar equipment?"
        elif any(word in last_message for word in ['sport', 'racing', 'athletic', 'exercise', 'fitness']):
            follow_up = "Has anyone else tried this activity?"
        elif any(word in last_message for word in ['pain', 'hurt', 'sore', 'ache']):
            follow_up = "What pain management strategies have others found helpful?"
        elif any(word in last_message for word in ['tech', 'app', 'device', 'phone', 'computer']):
            follow_up = "What other helpful tech tools are people using?"
        elif any(word in last_message for word in ['work', 'job', 'career', 'employment']):
            follow_up = "How have others navigated workplace accommodations?"
        elif any(word in last_message for word in ['travel', 'trip', 'vacation', 'flying']):
            follow_up = "What are your best travel tips for accessibility?"
        elif any(word in last_message for word in ['help', 'advice', 'tips', 'suggestions']):
            follow_up = "What has everyone else found helpful in similar situations?"
        elif any(word in last_message for word in ['new', 'first time', 'just got', 'recently']):
            follow_up = "What advice would others give to someone just starting out?"
        elif any(word in last_message for word in ['problem', 'issue', 'trouble', 'difficult']):
            follow_up = "How have others dealt with similar challenges?"
        else:
            # Default follow-up for general questions
            follow_up = "What experiences have others had with this?"
        
        # Add follow-up if we found a good one (always add when applicable)
        if follow_up:
            return f"{response}\n\n{follow_up}"
        
        return response
