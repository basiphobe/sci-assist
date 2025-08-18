"""
Database repository layer for the Discord LLM Bot.

This module provides a clean data access layer using the repository pattern,
abstracting database operations and providing high-level methods for
managing conversations, messages, and users.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from discord_llm_bot.config import DatabaseConfig
from discord_llm_bot.utils.logging import get_logger, log_function_call
from discord_llm_bot.utils.exceptions import DatabaseError
from discord_llm_bot.database.models import Base, User, Conversation, Message


class DatabaseManager:
    """
    Database manager providing high-level database operations.
    
    This class manages database connections, transactions, and provides
    repository methods for all database operations. It handles both
    sync and async operations and includes connection pooling and
    error handling.
    
    Attributes:
        config: Database configuration
        engine: SQLAlchemy async engine
        session_factory: Async session factory
    """
    
    def __init__(self, config: DatabaseConfig) -> None:
        """
        Initialize the database manager.
        
        Args:
            config: Database configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        self.engine = None
        self.session_factory = None
        self._closed = False
        
        log_function_call("DatabaseManager.__init__", database_url=config.url)
    
    async def initialize(self) -> None:
        """
        Initialize the database connection and create tables.
        
        This method sets up the database connection, creates tables if
        they don't exist, and prepares the session factory.
        
        Raises:
            DatabaseError: If database initialization fails
        """
        if self._closed:
            raise DatabaseError("Database manager has been closed")
        
        try:
            self.logger.info("Initializing database connection")
            
            # Convert SQLite URL to async if needed
            database_url = self.config.url
            if database_url.startswith("sqlite:///"):
                database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
            elif database_url.startswith("postgresql://"):
                database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
            
            # Create async engine
            self.engine = create_async_engine(
                database_url,
                echo=self.config.echo,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,   # Recycle connections every hour
            )
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            
            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            self.logger.info("Database initialization completed")
            
        except Exception as e:
            self.logger.error("Failed to initialize database", error=str(e))
            raise DatabaseError(
                "Failed to initialize database",
                context={"database_url": self.config.url},
                original_error=e,
            )
    
    @asynccontextmanager
    async def get_session(self):
        """
        Get a database session with automatic cleanup.
        
        This context manager provides a database session with automatic
        transaction management and cleanup.
        
        Yields:
            AsyncSession: Database session
            
        Example:
            ```python
            async with db_manager.get_session() as session:
                user = await session.get(User, user_id)
                # ... perform operations
                await session.commit()
            ```
        """
        if not self.session_factory:
            raise DatabaseError("Database not initialized")
        
        session = self.session_factory()
        try:
            yield session
        except Exception as e:
            await session.rollback()
            self.logger.error("Database session error", error=str(e))
            raise
        finally:
            await session.close()
    
    async def health_check(self) -> bool:
        """
        Perform a health check on the database connection.
        
        Returns:
            True if the database is healthy, False otherwise
        """
        try:
            async with self.get_session() as session:
                await session.execute(select(1))
            return True
        except Exception as e:
            self.logger.warning("Database health check failed", error=str(e))
            return False
    
    # User management methods
    
    async def get_or_create_user(
        self,
        discord_id: int,
        username: str,
        display_name: Optional[str] = None,
    ) -> User:
        """
        Get an existing user or create a new one.
        
        Args:
            discord_id: Discord user ID
            username: Discord username
            display_name: Discord display name
            
        Returns:
            User object
        """
        log_function_call("get_or_create_user", discord_id=discord_id, username=username)
        
        async with self.get_session() as session:
            # Try to get existing user
            stmt = select(User).where(User.discord_id == discord_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                # Update username/display_name if changed
                if user.username != username or user.display_name != display_name:
                    user.username = username
                    user.display_name = display_name
                    user.updated_at = datetime.utcnow()
                    await session.commit()
                return user
            
            # Create new user
            user = User(
                discord_id=discord_id,
                username=username,
                display_name=display_name,
            )
            session.add(user)
            await session.commit()
            
            self.logger.debug("Created new user", user_id=user.id, discord_id=discord_id)
            return user
    
    async def get_user_by_discord_id(self, discord_id: int) -> Optional[User]:
        """
        Get a user by Discord ID.
        
        Args:
            discord_id: Discord user ID
            
        Returns:
            User object or None if not found
        """
        async with self.get_session() as session:
            stmt = select(User).where(User.discord_id == discord_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    # Conversation management methods
    
    async def get_or_create_conversation(
        self,
        user_id: int,
        channel_id: int,
        guild_id: Optional[int] = None,
    ) -> Conversation:
        """
        Get an existing conversation or create a new one.
        
        Args:
            user_id: Database user ID
            channel_id: Discord channel ID
            guild_id: Discord guild ID
            
        Returns:
            Conversation object
        """
        log_function_call(
            "get_or_create_conversation",
            user_id=user_id,
            channel_id=channel_id,
            guild_id=guild_id,
        )
        
        async with self.get_session() as session:
            # Try to get existing conversation
            stmt = select(Conversation).where(
                and_(
                    Conversation.user_id == user_id,
                    Conversation.channel_id == channel_id,
                    Conversation.guild_id == guild_id,
                    Conversation.is_active == True,
                )
            )
            result = await session.execute(stmt)
            conversation = result.scalar_one_or_none()
            
            if conversation:
                return conversation
            
            # Create new conversation
            conversation = Conversation(
                user_id=user_id,
                channel_id=channel_id,
                guild_id=guild_id,
            )
            session.add(conversation)
            await session.commit()
            
            self.logger.debug("Created new conversation", conversation_id=conversation.id)
            return conversation
    
    async def get_conversation_messages(
        self,
        conversation_id: int,
        limit: Optional[int] = None,
        include_deleted: bool = False,
    ) -> List[Message]:
        """
        Get messages for a conversation.
        
        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to return
            include_deleted: Whether to include deleted messages
            
        Returns:
            List of Message objects
        """
        async with self.get_session() as session:
            stmt = select(Message).where(Message.conversation_id == conversation_id)
            
            if not include_deleted:
                stmt = stmt.where(Message.is_deleted == False)
            
            # Order by created_at DESC to get most recent messages first
            stmt = stmt.order_by(Message.created_at.desc())
            
            if limit:
                stmt = stmt.limit(limit)
            
            result = await session.execute(stmt)
            messages = list(result.scalars().all())
            
            # Reverse to get chronological order (oldest first)
            messages.reverse()
            
            return messages
    
    async def add_message(
        self,
        conversation_id: int,
        user_id: int,
        role: str,
        content: str,
        token_count: int = 0,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID
            role: Message role (user, assistant, system)
            content: Message content
            token_count: Number of tokens in the message
            extra_data: Additional metadata
            
        Returns:
            Created Message object
        """
        log_function_call(
            "add_message",
            conversation_id=conversation_id,
            role=role,
            content_length=len(content),
            token_count=token_count,
        )
        
        async with self.get_session() as session:
            # Create message
            message = Message(
                conversation_id=conversation_id,
                user_id=user_id,
                role=role,
                content=content,
                token_count=token_count,
                extra_data=extra_data,
            )
            session.add(message)
            
            # Update conversation counters
            stmt = (
                update(Conversation)
                .where(Conversation.id == conversation_id)
                .values(
                    message_count=Conversation.message_count + 1,
                    total_tokens=Conversation.total_tokens + token_count,
                    updated_at=datetime.utcnow(),
                )
            )
            await session.execute(stmt)
            
            await session.commit()
            
            self.logger.debug("Added message", message_id=message.id, conversation_id=conversation_id)
            return message
    
    async def reset_conversation(self, conversation_id: int) -> None:
        """
        Reset a conversation by marking all messages as deleted.
        
        Args:
            conversation_id: Conversation ID
        """
        log_function_call("reset_conversation", conversation_id=conversation_id)
        
        async with self.get_session() as session:
            # Mark all messages as deleted
            stmt = (
                update(Message)
                .where(Message.conversation_id == conversation_id)
                .values(is_deleted=True)
            )
            await session.execute(stmt)
            
            # Reset conversation counters
            stmt = (
                update(Conversation)
                .where(Conversation.id == conversation_id)
                .values(
                    message_count=0,
                    total_tokens=0,
                    updated_at=datetime.utcnow(),
                )
            )
            await session.execute(stmt)
            
            await session.commit()
            
            self.logger.debug("Reset conversation", conversation_id=conversation_id)
    
    async def get_conversation_stats(self, conversation_id: int) -> Dict[str, Any]:
        """
        Get statistics for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Dictionary with conversation statistics
        """
        async with self.get_session() as session:
            # Get conversation with basic stats
            stmt = select(Conversation).where(Conversation.id == conversation_id)
            result = await session.execute(stmt)
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                raise DatabaseError(f"Conversation {conversation_id} not found")
            
            # Get additional stats
            message_stmt = select(func.count(Message.id)).where(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.is_deleted == False,
                )
            )
            result = await session.execute(message_stmt)
            active_message_count = result.scalar() or 0
            
            # Get last message timestamp
            last_message_stmt = (
                select(Message.created_at)
                .where(
                    and_(
                        Message.conversation_id == conversation_id,
                        Message.is_deleted == False,
                    )
                )
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            result = await session.execute(last_message_stmt)
            last_message_time = result.scalar()
            
            return {
                "conversation_id": conversation_id,
                "message_count": active_message_count,
                "total_tokens": conversation.total_tokens,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
                "last_message": last_message_time,
            }
    
    async def cleanup_old_conversations(self, days: int = 30) -> int:
        """
        Clean up old conversations and their messages.
        
        Args:
            days: Number of days after which to clean up conversations
            
        Returns:
            Number of conversations cleaned up
        """
        log_function_call("cleanup_old_conversations", days=days)
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        async with self.get_session() as session:
            # Find old conversations
            stmt = select(Conversation.id).where(
                and_(
                    Conversation.updated_at < cutoff_date,
                    Conversation.is_active == True,
                )
            )
            result = await session.execute(stmt)
            old_conversation_ids = [row[0] for row in result.fetchall()]
            
            if not old_conversation_ids:
                return 0
            
            # Mark conversations as inactive
            stmt = (
                update(Conversation)
                .where(Conversation.id.in_(old_conversation_ids))
                .values(is_active=False)
            )
            await session.execute(stmt)
            
            # Mark messages as deleted
            stmt = (
                update(Message)
                .where(Message.conversation_id.in_(old_conversation_ids))
                .values(is_deleted=True)
            )
            await session.execute(stmt)
            
            await session.commit()
            
            count = len(old_conversation_ids)
            self.logger.info("Cleaned up old conversations", count=count, cutoff_date=cutoff_date)
            return count
    
    async def close(self) -> None:
        """Close the database connection and clean up resources."""
        if not self._closed:
            self.logger.debug("Closing database manager")
            
            if self.engine:
                await self.engine.dispose()
            
            self._closed = True
            self.logger.debug("Database manager closed")
