"""
Database models for the Discord LLM Bot.

This module defines SQLAlchemy models for storing conversation data,
user information, and message history in a relational database.
The models are designed to be simple, efficient, and support
the conversation management features of the bot.
"""

from datetime import datetime
from typing import Optional, Dict, Any
import json

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    BigInteger,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON

Base = declarative_base()


class User(Base):
    """
    User model for storing Discord user information.
    
    This model stores basic information about Discord users who have
    interacted with the bot. It's used for user preferences and
    conversation association.
    
    Attributes:
        id: Primary key
        discord_id: Discord user ID (unique)
        username: Discord username
        display_name: Discord display name
        created_at: When the user record was created
        updated_at: When the user record was last updated
        preferences: JSON field for user preferences
        is_active: Whether the user is active
    """
    
    __tablename__ = "users"
    
    id: Mapped[int] = Column(Integer, primary_key=True)
    discord_id: Mapped[int] = Column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str] = Column(String(32), nullable=False)
    display_name: Mapped[Optional[str]] = Column(String(32), nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    preferences: Mapped[Optional[Dict[str, Any]]] = Column(JSON, nullable=True)
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="user")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="user")
    
    def __repr__(self) -> str:
        """Return string representation of the user."""
        return f"<User(id={self.id}, discord_id={self.discord_id}, username='{self.username}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the user to a dictionary."""
        return {
            "id": self.id,
            "discord_id": self.discord_id,
            "username": self.username,
            "display_name": self.display_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "preferences": self.preferences,
            "is_active": self.is_active,
        }


class Conversation(Base):
    """
    Conversation model for storing conversation metadata.
    
    This model represents a conversation context, which can be associated
    with a specific Discord channel, guild, or DM. It tracks the overall
    conversation state and settings.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        channel_id: Discord channel ID
        guild_id: Discord guild ID (nullable for DMs)
        created_at: When the conversation was created
        updated_at: When the conversation was last updated
        is_active: Whether the conversation is active
        extra_data: JSON field for conversation metadata
        message_count: Cached count of messages
        total_tokens: Cached count of total tokens used
    """
    
    __tablename__ = "conversations"
    
    id: Mapped[int] = Column(Integer, primary_key=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel_id: Mapped[int] = Column(BigInteger, nullable=False, index=True)
    guild_id: Mapped[Optional[int]] = Column(BigInteger, nullable=True, index=True)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    extra_data: Mapped[Optional[Dict[str, Any]]] = Column(JSON, nullable=True)
    message_count: Mapped[int] = Column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = Column(Integer, default=0, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation", order_by="Message.created_at")
    
    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_conversations_user_channel", "user_id", "channel_id"),
        Index("idx_conversations_guild_channel", "guild_id", "channel_id"),
        Index("idx_conversations_updated", "updated_at"),
    )
    
    def __repr__(self) -> str:
        """Return string representation of the conversation."""
        return f"<Conversation(id={self.id}, user_id={self.user_id}, channel_id={self.channel_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the conversation to a dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "guild_id": self.guild_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
            "extra_data": self.extra_data,
            "message_count": self.message_count,
            "total_tokens": self.total_tokens,
        }


class Message(Base):
    """
    Message model for storing individual conversation messages.
    
    This model stores individual messages within conversations, including
    both user messages and AI responses. It supports rich metadata and
    token tracking for context management.
    
    Attributes:
        id: Primary key
        conversation_id: Foreign key to Conversation
        user_id: Foreign key to User
        role: Message role (user, assistant, system)
        content: Message content
        created_at: When the message was created
        token_count: Number of tokens in the message
        extra_data: JSON field for message metadata
        is_deleted: Whether the message is deleted
    """
    
    __tablename__ = "messages"
    
    id: Mapped[int] = Column(Integer, primary_key=True)
    conversation_id: Mapped[int] = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = Column(String(16), nullable=False)  # user, assistant, system
    content: Mapped[str] = Column(Text, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    token_count: Mapped[int] = Column(Integer, default=0, nullable=False)
    extra_data: Mapped[Optional[Dict[str, Any]]] = Column(JSON, nullable=True)
    is_deleted: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    user: Mapped["User"] = relationship("User", back_populates="messages")
    
    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_messages_conversation", "conversation_id"),
        Index("idx_messages_conversation_created", "conversation_id", "created_at"),
        Index("idx_messages_user", "user_id"),
        Index("idx_messages_role", "role"),
    )
    
    def __repr__(self) -> str:
        """Return string representation of the message."""
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, role='{self.role}', content='{content_preview}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary."""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "token_count": self.token_count,
            "extra_data": self.extra_data,
            "is_deleted": self.is_deleted,
        }
    
    def to_chat_message(self) -> Dict[str, str]:
        """Convert to LLM chat message format."""
        return {
            "role": self.role,
            "content": self.content,
        }
