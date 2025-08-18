"""
Configuration management for the Discord LLM Bot.

This module handles all configuration loading from environment variables,
validation, and provides typed configuration objects for use throughout
the application.

The configuration is loaded from environment variables and .env files,
with sensible defaults for development and clear documentation for
production deployment.
"""

import os
from pathlib import Path
from typing import Optional, List

from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(
        default="sqlite:///./bot_conversations.db",
        description="Database connection URL"
    )
    echo: bool = Field(
        default=False,
        description="Echo SQL queries to logs"
    )
    
    class Config:
        env_prefix = "DATABASE_"


class DiscordConfig(BaseSettings):
    """Discord bot configuration settings."""
    
    token: str = Field(
        ...,
        description="Discord bot token from Developer Portal"
    )
    guild_id: Optional[int] = Field(
        default=None,
        description="Optional guild ID for testing (enables sync)"
    )
    command_prefix: str = Field(
        default="!",
        description="Command prefix for text commands"
    )
    avatar_path: Optional[str] = Field(
        default=None,
        description="Path to bot avatar image file"
    )
    
    class Config:
        env_prefix = "DISCORD_"
        
    @validator("token")
    def validate_token(cls, v: str) -> str:
        """Validate Discord token format."""
        if not v or len(v) < 50:
            raise ValueError("Discord token must be a valid bot token")
        return v


class LLMConfig(BaseSettings):
    """LLM API configuration settings."""
    
    api_url: str = Field(
        default="http://localhost:8000/v1/chat/completions",
        description="LLM API endpoint URL"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Optional API key for LLM service"
    )
    model_name: str = Field(
        default="local-model",
        description="Name of the model to use"
    )
    max_tokens: int = Field(
        default=2048,
        gt=0,
        le=8192,
        description="Maximum tokens in response"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature"
    )
    timeout: int = Field(
        default=30,
        gt=0,
        description="Request timeout in seconds"
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Default system prompt for conversations"
    )
    system_prompt_file: Optional[str] = Field(
        default=None,
        description="Path to file containing system prompt"
    )
    
    class Config:
        env_prefix = "LLM_"
    
    def get_system_prompt(self) -> Optional[str]:
        """Get the system prompt, loading from file if specified."""
        if self.system_prompt_file:
            try:
                from pathlib import Path
                prompt_file = Path(self.system_prompt_file)
                if prompt_file.exists():
                    return prompt_file.read_text(encoding='utf-8').strip()
            except Exception:
                # Fall back to direct system_prompt if file loading fails
                pass
        return self.system_prompt


class RAGConfig(BaseSettings):
    """RAG (Retrieval-Augmented Generation) configuration."""
    
    enabled: bool = Field(
        default=True,
        description="Enable RAG system for enhanced responses"
    )
    
    # Keywords that trigger RAG usage
    trigger_keywords: List[str] = Field(
        default=[
            # Medical terms
            "autonomic dysreflexia", "neurogenic bladder", "spasticity", "pressure sores",
            "dysphagia", "orthostatic hypotension", "heterotopic ossification",
            # Research/evidence terms  
            "research", "studies", "clinical trials", "evidence", "latest", "recent",
            # Treatment terms
            "treatment", "therapy", "rehabilitation", "intervention", "medication",
            # Equipment terms
            "wheelchair", "cushion", "transfer board", "hand controls", "adaptive equipment"
        ],
        description="Keywords that trigger RAG enhancement"
    )
    
    # Confidence threshold for RAG usage
    confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score to use RAG results"
    )
    
    # Source attribution
    include_sources: bool = Field(
        default=True,
        description="Include Wikipedia source attribution in responses"
    )
    
    class Config:
        env_prefix = "RAG_"


class ConversationConfig(BaseSettings):
    """Conversation management configuration."""
    
    max_history: int = Field(
        default=20,
        gt=0,
        description="Maximum messages to keep in conversation history"
    )
    context_window_tokens: int = Field(
        default=4096,
        gt=0,
        description="Maximum tokens for conversation context"
    )
    auto_cleanup_days: int = Field(
        default=30,
        gt=0,
        description="Days after which to cleanup old conversations"
    )
    shared_context_channel_id: Optional[int] = Field(
        default=None,
        description="Channel ID for shared context conversations (None for no shared context)"
    )
    
    class Config:
        env_prefix = "CONVERSATION_"


class LoggingConfig(BaseSettings):
    """Logging configuration settings."""
    
    level: str = Field(
        default="INFO",
        description="Logging level"
    )
    format: str = Field(
        default="json",
        description="Log format: 'json' or 'text'"
    )
    
    class Config:
        env_prefix = "LOG_"
        
    @validator("level")
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
        
    @validator("format")
    def validate_format(cls, v: str) -> str:
        """Validate log format."""
        if v not in {"json", "text"}:
            raise ValueError("Log format must be 'json' or 'text'")
        return v


class AppConfig(BaseSettings):
    """Main application configuration."""
    
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    dev_mode: bool = Field(
        default=False,
        description="Enable development mode features"
    )
    
    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    conversation: ConversationConfig = Field(default_factory=ConversationConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    class Config:
        # Load from .env file if present
        env_file = ".env"
        env_file_encoding = "utf-8"
        
    def __init__(self, **kwargs):
        """Initialize configuration with sub-configs."""
        super().__init__(**kwargs)
        
        # Initialize sub-configurations with environment variables
        self.database = DatabaseConfig()
        self.discord = DiscordConfig()
        self.llm = LLMConfig()
        self.rag = RAGConfig()
        self.conversation = ConversationConfig()
        self.logging = LoggingConfig()


def load_config() -> AppConfig:
    """
    Load and validate application configuration.
    
    This function loads configuration from environment variables and .env files,
    validates all settings, and returns a fully configured AppConfig instance.
    
    Returns:
        AppConfig: Validated application configuration
        
    Raises:
        ValidationError: If configuration is invalid
        FileNotFoundError: If required environment variables are missing
        
    Example:
        ```python
        config = load_config()
        print(f"Bot will connect to: {config.llm.api_url}")
        ```
    """
    # Check for .env file and load it
    env_file = Path(".env")
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
    
    return AppConfig()


# Global configuration instance
# This is loaded once when the module is imported
try:
    config = load_config()
except Exception as e:
    # In case of configuration errors during import, create a minimal config
    # This allows the module to be imported for testing or documentation
    print(f"Warning: Failed to load configuration: {e}")
    config = None
