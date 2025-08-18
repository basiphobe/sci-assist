"""
Conversation memory management for the Discord LLM Bot.

This module handles intelligent memory management for conversations,
including context window management, message prioritization, and
token counting to ensure optimal performance within LLM limits.
"""

import tiktoken
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from discord_llm_bot.config import ConversationConfig
from discord_llm_bot.utils.logging import get_logger, log_function_call
from discord_llm_bot.llm.models import ChatMessage, MessageRole
from discord_llm_bot.database.models import Message


class MemoryManager:
    """
    Manages conversation memory and context windows.
    
    This class handles the intelligent management of conversation history
    to fit within token limits while preserving important context and
    conversation flow.
    
    Key Features:
    - Token counting with tiktoken
    - Context window management
    - Message prioritization
    - Smart truncation strategies
    - Conversation summarization (future)
    
    Attributes:
        config: Conversation configuration
        encoder: Tiktoken encoder for token counting
    """
    
    def __init__(self, config: ConversationConfig) -> None:
        """
        Initialize the memory manager.
        
        Args:
            config: Conversation configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # Initialize tiktoken encoder for token counting
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
        except Exception:
            # Fallback to a simple token counting method
            self.encoder = None
            self.logger.warning("Failed to load tiktoken encoder, using fallback token counting")
        
        log_function_call(
            "MemoryManager.__init__",
            context_window_tokens=config.context_window_tokens,
            max_history=config.max_history,
        )
    
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception:
                # Fallback to simple counting
                pass
        
        # Simple fallback: roughly 4 characters per token
        return max(1, len(text) // 4)
    
    def count_message_tokens(self, message: ChatMessage) -> int:
        """
        Count tokens for a chat message including role overhead.
        
        Args:
            message: Chat message to count tokens for
            
        Returns:
            Number of tokens including overhead
        """
        # Count content tokens
        content_tokens = self.count_tokens(message.content)
        
        # Add overhead for role and formatting (roughly 4 tokens per message)
        overhead_tokens = 4
        
        # Add name tokens if present
        if message.name:
            overhead_tokens += self.count_tokens(message.name)
        
        return content_tokens + overhead_tokens
    
    def count_messages_tokens(self, messages: List[ChatMessage]) -> int:
        """
        Count total tokens for a list of messages.
        
        Args:
            messages: List of chat messages
            
        Returns:
            Total number of tokens
        """
        total_tokens = 0
        
        for message in messages:
            total_tokens += self.count_message_tokens(message)
        
        # Add a small overhead for the conversation structure
        total_tokens += 10
        
        return total_tokens
    
    def prepare_context(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
    ) -> Tuple[List[ChatMessage], int]:
        """
        Prepare conversation context within token limits.
        
        This method takes a list of database messages and converts them
        to ChatMessage format while ensuring they fit within the context
        window limits. It uses intelligent truncation strategies to
        preserve the most important parts of the conversation.
        
        Args:
            messages: List of database messages
            system_prompt: Optional system prompt to include
            
        Returns:
            Tuple of (chat_messages, total_tokens)
        """
        log_function_call(
            "prepare_context",
            message_count=len(messages),
            system_prompt_length=len(system_prompt) if system_prompt else 0,
        )
        
        chat_messages: List[ChatMessage] = []
        
        # Add system prompt if provided
        if system_prompt:
            system_message = ChatMessage(
                role=MessageRole.SYSTEM,
                content=system_prompt
            )
            chat_messages.append(system_message)
        
        # Convert database messages to chat messages
        all_messages = []
        for msg in messages:
            if msg.is_deleted:
                continue
                
            chat_msg = ChatMessage(
                role=MessageRole(msg.role),
                content=msg.content,
                extra_data=msg.extra_data,
            )
            all_messages.append(chat_msg)
        
        # Apply truncation strategy to fit within limits
        context_messages = self._apply_truncation_strategy(
            all_messages,
            available_tokens=self.config.context_window_tokens - (
                self.count_message_tokens(chat_messages[0]) if chat_messages else 0
            )
        )
        
        # Combine system prompt with context messages
        chat_messages.extend(context_messages)
        
        # Count final tokens
        total_tokens = self.count_messages_tokens(chat_messages)
        
        self.logger.debug(
            "Prepared conversation context",
            final_message_count=len(chat_messages),
            total_tokens=total_tokens,
            context_usage=f"{total_tokens}/{self.config.context_window_tokens}",
        )
        
        return chat_messages, total_tokens
    
    def _apply_truncation_strategy(
        self,
        messages: List[ChatMessage],
        available_tokens: int,
    ) -> List[ChatMessage]:
        """
        Apply intelligent truncation to fit messages within token limits.
        
        This method uses a sliding window approach with some intelligence
        to preserve important parts of the conversation.
        
        Args:
            messages: List of messages to truncate
            available_tokens: Available token budget
            
        Returns:
            Truncated list of messages
        """
        if not messages:
            return []
        
        # Start with the most recent messages and work backwards
        result_messages = []
        used_tokens = 0
        
        # Always try to include the most recent exchange (user + assistant)
        for message in reversed(messages):
            message_tokens = self.count_message_tokens(message)
            
            if used_tokens + message_tokens <= available_tokens:
                result_messages.insert(0, message)
                used_tokens += message_tokens
            else:
                break
        
        # If we have very few messages, try to include more by summarizing
        if len(result_messages) < 4 and len(messages) > len(result_messages):
            # TODO: Implement conversation summarization
            # For now, just use what we have
            pass
        
        # Ensure we don't exceed the maximum history limit
        if len(result_messages) > self.config.max_history:
            result_messages = result_messages[-self.config.max_history:]
        
        self.logger.debug(
            "Applied truncation strategy",
            original_count=len(messages),
            final_count=len(result_messages),
            used_tokens=used_tokens,
            available_tokens=available_tokens,
        )
        
        return result_messages
    
    def should_cleanup_conversation(
        self,
        conversation_updated: datetime,
        message_count: int,
    ) -> bool:
        """
        Determine if a conversation should be cleaned up.
        
        Args:
            conversation_updated: When the conversation was last updated
            message_count: Number of messages in the conversation
            
        Returns:
            True if the conversation should be cleaned up
        """
        # Check age-based cleanup
        age_threshold = datetime.utcnow() - timedelta(days=self.config.auto_cleanup_days)
        if conversation_updated < age_threshold:
            return True
        
        # Check message count-based cleanup
        # Very long conversations might need cleanup
        if message_count > self.config.max_history * 5:
            return True
        
        return False
    
    def optimize_conversation_history(
        self,
        messages: List[Message],
    ) -> List[Message]:
        """
        Optimize conversation history by removing redundant messages.
        
        This method removes or consolidates messages to improve
        conversation flow and reduce token usage.
        
        Args:
            messages: List of messages to optimize
            
        Returns:
            Optimized list of messages
        """
        if not messages:
            return []
        
        optimized = []
        last_role = None
        
        for message in messages:
            # Skip deleted messages
            if message.is_deleted:
                continue
            
            # Consolidate consecutive messages from the same role
            if message.role == last_role and optimized:
                # Merge content with the previous message
                last_message = optimized[-1]
                last_message.content += f"\n\n{message.content}"
                last_message.token_count += message.token_count
            else:
                optimized.append(message)
                last_role = message.role
        
        return optimized
