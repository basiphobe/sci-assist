"""
Custom exceptions for the Discord LLM Bot.

This module defines a hierarchy of custom exceptions that provide clear
error handling and debugging information throughout the application.
All exceptions inherit from a base DiscordLLMBotError class for easy
catching and handling.
"""

from typing import Optional, Any, Dict


class DiscordLLMBotError(Exception):
    """
    Base exception class for all Discord LLM Bot errors.
    
    This is the root exception that all other custom exceptions inherit from.
    It provides a consistent interface and allows catching all bot-related
    errors with a single except clause.
    
    Attributes:
        message: Human-readable error message
        context: Additional context information about the error
        original_error: The original exception that caused this error (if any)
    """
    
    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the base exception.
        
        Args:
            message: Human-readable error message
            context: Additional context information
            original_error: The original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.original_error = original_error
        
    def __str__(self) -> str:
        """Return string representation of the error."""
        error_str = self.message
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            error_str += f" (Context: {context_str})"
        if self.original_error:
            error_str += f" (Caused by: {self.original_error})"
        return error_str


class ConfigurationError(DiscordLLMBotError):
    """
    Raised when there's an error in configuration.
    
    This exception is raised when:
    - Required environment variables are missing
    - Configuration values are invalid
    - Configuration files cannot be loaded
    
    Example:
        ```python
        if not discord_token:
            raise ConfigurationError(
                "Discord token is required",
                context={"env_var": "DISCORD_TOKEN"}
            )
        ```
    """
    pass


class LLMAPIError(DiscordLLMBotError):
    """
    Raised when there's an error communicating with the LLM API.
    
    This exception is raised when:
    - LLM API is unreachable
    - API returns an error response
    - Request times out
    - Authentication fails
    
    Example:
        ```python
        try:
            response = await llm_client.generate(prompt)
        except httpx.HTTPError as e:
            raise LLMAPIError(
                "Failed to communicate with LLM API",
                context={"url": api_url, "status": e.response.status_code},
                original_error=e
            )
        ```
    """
    pass


class ConversationError(DiscordLLMBotError):
    """
    Raised when there's an error in conversation management.
    
    This exception is raised when:
    - Conversation context cannot be loaded
    - Message history is corrupted
    - Context window limits are exceeded
    - Conversation state is invalid
    
    Example:
        ```python
        if len(conversation.messages) > max_history:
            raise ConversationError(
                "Conversation history exceeds maximum length",
                context={
                    "current_length": len(conversation.messages),
                    "max_length": max_history
                }
            )
        ```
    """
    pass


class DatabaseError(DiscordLLMBotError):
    """
    Raised when there's a database operation error.
    
    This exception is raised when:
    - Database connection fails
    - SQL operations fail
    - Data integrity constraints are violated
    - Migration errors occur
    
    Example:
        ```python
        try:
            session.commit()
        except SQLAlchemyError as e:
            raise DatabaseError(
                "Failed to save conversation to database",
                context={"conversation_id": conversation.id},
                original_error=e
            )
        ```
    """
    pass


class DiscordAPIError(DiscordLLMBotError):
    """
    Raised when there's an error with Discord API operations.
    
    This exception is raised when:
    - Discord API rate limits are hit
    - Bot permissions are insufficient
    - Discord API returns unexpected errors
    - Message sending fails
    
    Example:
        ```python
        try:
            await channel.send(message)
        except discord.HTTPException as e:
            raise DiscordAPIError(
                "Failed to send message to Discord",
                context={"channel_id": channel.id, "message_length": len(message)},
                original_error=e
            )
        ```
    """
    pass
