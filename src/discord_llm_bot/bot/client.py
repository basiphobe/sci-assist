"""
Discord bot client implementation.

This module contains the main Discord bot client that handles all Discord
interactions, integrates with the LLM service, and manages conversations
across Discord channels and users.

The bot supports both slash commands and message-based interactions,
with intelligent conversation threading and context management.
"""

import asyncio
from typing import Optional, Dict, Any, TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from discord_llm_bot.api.server import InternalAPIServer

from discord_llm_bot.config import AppConfig
from discord_llm_bot.utils.logging import (
    get_logger, 
    log_error, 
    log_discord_event,
    log_conversation_event,
    log_operation_timing,
    generate_correlation_id,
)
from discord_llm_bot.utils.exceptions import DiscordAPIError, ConversationError
from discord_llm_bot.llm.client import LLMClient
from discord_llm_bot.conversation.manager import ConversationManager
from discord_llm_bot.database.repositories import DatabaseManager


class DiscordLLMBot(commands.Bot):
    """
    Main Discord bot client with LLM integration.
    
    This class extends discord.py's Bot class to provide LLM-powered
    conversations with persistent memory and context management.
    
    Key Features:
    - Slash command support for modern Discord UX
    - Message-based interactions with @mentions and replies
    - Persistent conversation history across sessions
    - Context-aware responses with token management
    - Multi-user and multi-channel conversation support
    
    Attributes:
        config: Application configuration
        llm_client: Client for LLM API communication
        conversation_manager: Manages conversation state and history
        db_manager: Database operations manager
    """
    
    def __init__(self, config: AppConfig) -> None:
        """
        Initialize the Discord LLM Bot.
        
        Args:
            config: Application configuration containing all settings
        """
        # Set up Discord intents (permissions for the bot)
        intents = discord.Intents.default()
        # Enable message content intent for reading message text
        intents.message_content = True  # Required for context awareness and message storage
        intents.guilds = True
        intents.guild_messages = True
        intents.dm_messages = True
        intents.presences = True  # For online status visibility
        
        # Initialize the bot with modern slash command support
        super().__init__(
            command_prefix=config.discord.command_prefix,
            intents=intents,
            help_command=None,  # We'll implement custom help
        )
        
        self.config = config
        self.logger = get_logger(__name__)
        
        # These will be initialized in setup()
        self.llm_client: Optional[LLMClient] = None
        self.conversation_manager: Optional[ConversationManager] = None
        self.db_manager: Optional[DatabaseManager] = None
        self.api_server: Optional["InternalAPIServer"] = None
        
        # Track if setup has been completed
        self._setup_complete = False
        
    async def setup(self) -> None:
        """
        Set up all bot components.
        
        This method initializes the database, LLM client, and conversation
        manager. It must be called before starting the bot.
        
        Raises:
            ConfigurationError: If setup fails
        """
        if self._setup_complete:
            return
            
        self.logger.info("Setting up Discord LLM Bot components")
        
        try:
            # Initialize database manager
            self.db_manager = DatabaseManager(self.config.database)
            await self.db_manager.initialize()
            
            # Initialize LLM client
            self.llm_client = LLMClient(self.config.llm)
            
            # Initialize conversation manager
            self.conversation_manager = ConversationManager(
                config=self.config,
                llm_client=self.llm_client,
                db_manager=self.db_manager,
            )
            
            # Load bot commands and events
            await self._load_commands()
            await self._load_events()
            
            # Initialize internal API server
            from discord_llm_bot.api.server import InternalAPIServer
            self.api_server = InternalAPIServer(self, port=8765)
            await self.api_server.start()
            
            self._setup_complete = True
            self.logger.info("Bot setup completed successfully")
            
        except Exception as e:
            self.logger.error("Failed to set up bot components", error=str(e))
            raise
    
    async def _load_commands(self) -> None:
        """Load slash commands and text commands."""
        self.logger.debug("Loading bot commands")
        
        # Import and load command modules
        from discord_llm_bot.bot.commands import setup_commands
        await setup_commands(self)
        
    async def _load_events(self) -> None:
        """Load event handlers."""
        self.logger.debug("Loading event handlers")
        
        # Import and load event handlers
        from discord_llm_bot.bot.events import setup_events
        await setup_events(self)
    
    async def on_ready(self) -> None:
        """Called when the bot is ready and connected to Discord."""
        guild_count = len(self.guilds)
        user_count = sum(guild.member_count or 0 for guild in self.guilds)
        
        # Log the ready event
        log_discord_event(
            "bot_ready",
            bot_user=str(self.user),
            bot_id=self.user.id if self.user else None,
            guild_count=guild_count,
            user_count=user_count,
            shard_count=self.shard_count,
        )
        
        self.logger.info(
            "Bot is ready and connected to Discord",
            bot_user=str(self.user),
            guild_count=guild_count,
            user_count=user_count,
        )
        
        # Set bot status to online
        try:
            await self.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(
                    type=discord.ActivityType.listening,
                    name="your messages"
                )
            )
            self.logger.info("Bot status set to online")
        except Exception as e:
            self.logger.warning("Failed to set bot status", error=str(e))
        
        # Update avatar if configured
        avatar_path = getattr(self.config.discord, 'avatar_path', None)
        if avatar_path:
            try:
                from discord_llm_bot.utils.avatar import update_bot_avatar
                await update_bot_avatar(self, avatar_path, force_update=False)
                self.logger.info("Avatar updated successfully", avatar_path=avatar_path)
            except Exception as e:
                self.logger.warning("Failed to update avatar", error=str(e), avatar_path=avatar_path)
        
        # Sync commands globally (available in all servers)
        try:
            synced = await self.tree.sync()
            log_discord_event(
                "commands_synced_global",
                command_count=len(synced)
            )
            self.logger.info(f"Synced {len(synced)} commands globally")
        except Exception as e:
            self.logger.error("Failed to sync commands globally", error=str(e))
        
        # Set bot presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="your questions | /help"
            )
        )
    
    async def on_message(self, message: discord.Message) -> None:
        """
        Handle incoming messages.
        
        This method processes all messages, stores them for context,
        and determines if the bot should respond based on mentions, replies, or DMs.
        
        Args:
            message: The Discord message object
        """
        # Ignore messages from bots (including ourselves)
        if message.author.bot:
            return
        
        # Log the message event
        log_discord_event(
            "message_received",
            user_id=message.author.id,
            username=str(message.author),
            display_name=message.author.display_name,
            channel_id=message.channel.id,
            guild_id=message.guild.id if message.guild else None,
            message_length=len(message.content),
            has_attachments=bool(message.attachments),
            is_dm=isinstance(message.channel, discord.DMChannel),
            mentions_bot=self.user in message.mentions if self.user else False,
        )
        
        # Check if the bot should respond to this message
        should_respond = await self._should_respond_to_message(message)
        
        # Only store for context if we're NOT going to respond 
        # (if we're responding, the message will be stored in _handle_conversation_message)
        if not should_respond:
            await self._store_message_for_context(message)
        
        if should_respond:
            correlation_id = generate_correlation_id()
            self.logger.info(
                "Processing message for bot response",
                user_id=message.author.id,
                channel_id=message.channel.id,
                correlation_id=correlation_id,
            )
            
            try:
                # Show typing indicator while processing
                async with message.channel.typing():
                    with log_operation_timing(
                        "handle_conversation_message",
                        user_id=message.author.id,
                        channel_id=message.channel.id,
                        correlation_id=correlation_id,
                    ):
                        await self._handle_conversation_message(message)
                    
            except Exception as e:
                log_error(e, {
                    "message_id": message.id,
                    "channel_id": message.channel.id,
                    "user_id": message.author.id,
                    "correlation_id": correlation_id,
                })
                await self._send_error_response(message, "Sorry, I encountered an error processing your message.")
        
        # Always process commands (for text-based commands)
        await self.process_commands(message)
    
    async def _should_respond_to_message(self, message: discord.Message) -> bool:
        """
        Determine if the bot should respond to a message.
        
        Args:
            message: The Discord message to check
            
        Returns:
            True if the bot should respond, False otherwise
        """
        # Always respond to DMs
        if isinstance(message.channel, discord.DMChannel):
            return True
        
        # Respond if bot is mentioned
        if self.user and self.user.mentioned_in(message):
            return True
        
        # Respond if replying to one of the bot's messages
        if (message.reference and 
            message.reference.message_id and
            isinstance(message.channel, (discord.TextChannel, discord.Thread))):
            
            try:
                referenced_message = await message.channel.fetch_message(
                    message.reference.message_id
                )
                if referenced_message.author == self.user:
                    return True
            except discord.NotFound:
                # Referenced message was deleted
                pass
        
        return False
    
    async def _store_message_for_context(self, message: discord.Message) -> None:
        """
        Store a message for conversation context without generating a response.
        
        This is used for shared context channels where the bot observes but
        doesn't respond to every message. It allows the bot to maintain context
        about ongoing conversations in channels.
        
        This ensures the bot has access to all channel context when it does respond,
        but only stores messages in channels configured for shared context.
        
        Args:
            message: The Discord message to store
        """
        if not self.conversation_manager:
            return  # Skip if conversation manager not initialized

        # Check if user has consented to data storage
        if not self.conversation_manager.privacy_manager.should_store_message(message.author.id):
            self.logger.debug(f"Skipping context storage for user {message.author.id} - no consent")
            return
        
        # Only store for context in shared context channels or DMs
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_shared_context_channel = (
            self.conversation_manager.config.shared_context_channel_id is not None and
            message.channel.id == self.conversation_manager.config.shared_context_channel_id
        )
        
        if not (is_dm or is_shared_context_channel):
            return  # Skip storage for non-shared channels
        
        try:
            # Get or create conversation for this context
            conversation_id = await self.conversation_manager.get_or_create_conversation(
                user_id=message.author.id,
                channel_id=message.channel.id,
                guild_id=message.guild.id if message.guild else None,
            )
            
            # Add user message to conversation for context
            await self.conversation_manager.add_message(
                conversation_id=conversation_id,
                content=message.content,
                role="user",
                extra_data={
                    "discord_message_id": message.id,
                    "discord_user_id": message.author.id,
                    "discord_username": str(message.author),
                    "discord_display_name": f"@{message.author.display_name}",
                    "stored_for_context": True,  # Flag to indicate this was stored for context only
                }
            )
        except Exception as e:
            # Log error but don't fail the entire message processing
            log_error(e, {
                "message_id": message.id,
                "channel_id": message.channel.id,
                "user_id": message.author.id,
                "operation": "store_message_for_context",
            })
    
    async def _handle_conversation_message(self, message: discord.Message) -> None:
        """
        Handle a conversation message and generate a response.
        
        Args:
            message: The Discord message to respond to
        """
        if not self.conversation_manager:
            raise ConversationError("Conversation manager not initialized")

        # Check if user has consented to data storage
        if not self.conversation_manager.privacy_manager.should_store_message(message.author.id):
            self.logger.info(f"User {message.author.id} has not consented to data storage - providing response without storing conversation")
            
            # Generate a direct response without storing the conversation
            try:
                # Get system prompt
                system_prompt = self.conversation_manager.default_system_prompt
                
                # Create a temporary conversation context with just this message
                temp_context = f"Current user: @{message.author.display_name}\n{message.author.display_name}: {message.content}"
                
                # Generate response
                response_content = await self.conversation_manager.llm_client.generate_response(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"{temp_context}\n\nPlease respond to this message. Note: This conversation is not being stored as the user has not provided consent for data retention."}
                    ]
                )
                
                # Send response but don't store anything
                await self._send_response(message, response_content)
                
                # Log the privacy-respecting interaction
                self.logger.info(f"Provided response to user {message.author.id} without data storage")
                return
                
            except Exception as e:
                self.logger.error(f"Error generating response for non-consented user: {e}")
                await message.channel.send(
                    f"I'd be happy to help, but I'm having trouble processing your request right now. "
                    f"Please try again or use `/privacy` to manage your data preferences."
                )
                return

        try:
            # Get or create conversation for this context
            conversation_id = await self.conversation_manager.get_or_create_conversation(
                user_id=message.author.id,
                channel_id=message.channel.id,
                guild_id=message.guild.id if message.guild else None,
            )
            
            # Add the user message to conversation (since we're responding, 
            # it wasn't stored for context)
            await self.conversation_manager.add_message(
                conversation_id=conversation_id,
                content=message.content,
                role="user",
                extra_data={
                    "discord_message_id": message.id,
                    "discord_user_id": message.author.id,
                    "discord_username": str(message.author),
                    "discord_display_name": f"@{message.author.display_name}",
                }
            )

            # Generate response from LLM
            response_content = await self.conversation_manager.generate_response(
                conversation_id=conversation_id,
                current_user_name=f"@{message.author.display_name}"
            )
            
            # Send response to Discord
            response_message = await self._send_response(message, response_content)
            
            # Add bot response to conversation
            if response_message:
                await self.conversation_manager.add_message(
                    conversation_id=conversation_id,
                    content=response_content,
                    role="assistant",
                    extra_data={
                        "discord_message_id": response_message.id,
                        "discord_user_id": self.user.id if self.user else None,
                        "discord_username": str(self.user) if self.user else "Bot",
                    }
                )
            
        except Exception as e:
            self.logger.error("Error handling conversation message", 
                            message_id=message.id, error=str(e))
            raise
    
    async def _send_response(self, original_message: discord.Message, content: str) -> Optional[discord.Message]:
        """
        Send a response message to Discord.
        
        Args:
            original_message: The message being replied to
            content: The response content
            
        Returns:
            The sent message, or None if sending failed
        """
        try:
            # Check if this is the shared context channel
            is_shared_context = (
                self.config.conversation.shared_context_channel_id is not None and
                original_message.channel.id == self.config.conversation.shared_context_channel_id
            )
            
            # Split long messages if needed (Discord has a 2000 character limit)
            chunks = self._split_message(content)
            
            sent_message = None
            for i, chunk in enumerate(chunks):
                if is_shared_context:
                    # In shared context channel, post directly to channel (no reply)
                    sent_message = await original_message.channel.send(chunk)
                else:
                    # In private contexts (DMs, other channels), reply to user
                    if i == 0:
                        sent_message = await original_message.reply(chunk)
                    else:
                        await original_message.channel.send(chunk)
            
            return sent_message
            
        except discord.HTTPException as e:
            raise DiscordAPIError(
                "Failed to send response message",
                context={
                    "channel_id": original_message.channel.id,
                    "content_length": len(content),
                },
                original_error=e
            )
    
    async def _send_error_response(self, message: discord.Message, error_text: str) -> None:
        """Send an error response to the user."""
        try:
            # Check if this is the shared context channel
            is_shared_context = (
                self.config.conversation.shared_context_channel_id is not None and
                message.channel.id == self.config.conversation.shared_context_channel_id
            )
            
            if is_shared_context:
                # In shared context channel, post directly to channel
                await message.channel.send(f"❌ {error_text}")
            else:
                # In private contexts, reply to user
                await message.reply(f"❌ {error_text}")
        except discord.HTTPException:
            # If we can't reply, try sending to the channel
            try:
                await message.channel.send(f"❌ {error_text}")
            except discord.HTTPException:
                # If all else fails, log the error
                self.logger.error("Failed to send error response", 
                                error_text=error_text,
                                message_id=message.id)
    
    def _split_message(self, content: str, max_length: int = 2000) -> list[str]:
        """
        Split a message into chunks that fit Discord's character limit.
        
        Args:
            content: The message content to split
            max_length: Maximum length per chunk
            
        Returns:
            List of message chunks
        """
        if len(content) <= max_length:
            return [content]
        
        chunks = []
        current_chunk = ""
        
        # Split by lines first to try to preserve formatting
        lines = content.split('\n')
        
        for line in lines:
            # If a single line is too long, we need to split it
            if len(line) > max_length:
                # If we have a current chunk, add it first
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Split the long line
                while len(line) > max_length:
                    chunks.append(line[:max_length])
                    line = line[max_length:]
                
                if line:
                    current_chunk = line
            else:
                # Check if adding this line would exceed the limit
                if len(current_chunk) + len(line) + 1 > max_length:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = line
                else:
                    if current_chunk:
                        current_chunk += '\n' + line
                    else:
                        current_chunk = line
        
        # Add the last chunk if there's content
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def close(self) -> None:
        """Clean up resources and close the bot."""
        self.logger.info("Shutting down Discord LLM Bot")
        
        try:
            # Stop internal API server
            if self.api_server:
                await self.api_server.stop()
            
            # Close database connections
            if self.db_manager:
                await self.db_manager.close()
            
            # Close LLM client
            if self.llm_client:
                await self.llm_client.close()
            
            # Close Discord connection
            await super().close()
            
        except Exception as e:
            self.logger.error("Error during bot shutdown", error=str(e))
            raise
        finally:
            self.logger.info("Bot shutdown complete")
