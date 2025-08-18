"""
Discord event handlers for the LLM bot.

This module contains event handlers that respond to Discord events
like errors, command failures, and other bot lifecycle events.
"""

import traceback
from typing import Any

import discord
from discord.ext import commands

from discord_llm_bot.utils.logging import (
    get_logger, 
    log_error, 
    log_discord_event,
    log_operation_timing,
)


async def setup_events(bot) -> None:
    """
    Set up event handlers for the bot.
    
    Args:
        bot: The Discord bot instance
    """
    logger = get_logger(__name__)
    logger.debug("Setting up event handlers")
    
    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
        """
        Handle command errors.
        
        Args:
            ctx: Command context
            error: The error that occurred
        """
        logger = get_logger(__name__)
        
        # Ignore command not found errors
        if isinstance(error, commands.CommandNotFound):
            return
        
        # Handle cooldown errors
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f} seconds.")
            return
        
        # Handle missing permissions
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
            return
        
        # Handle missing arguments
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
            return
        
        # Handle bad arguments
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument provided: {error}")
            return
        
        # Log and handle unexpected errors
        log_error(error, {
            "command": ctx.command.name if ctx.command else "unknown",
            "user_id": ctx.author.id,
            "channel_id": ctx.channel.id,
            "guild_id": ctx.guild.id if ctx.guild else None,
        })
        
        await ctx.send("❌ An unexpected error occurred while processing your command.")
    
    @bot.event
    async def on_app_command_error(
        interaction: discord.Interaction, 
        error: discord.app_commands.AppCommandError
    ) -> None:
        """
        Handle slash command errors.
        
        Args:
            interaction: The interaction that caused the error
            error: The error that occurred
        """
        logger = get_logger(__name__)
        
        # Handle cooldown errors
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f} seconds.",
                ephemeral=True
            )
            return
        
        # Handle missing permissions
        if isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        # Handle transformation errors (bad arguments)
        if isinstance(error, discord.app_commands.TransformerError):
            await interaction.response.send_message(
                f"❌ Invalid argument provided: {error}",
                ephemeral=True
            )
            return
        
        # Log and handle unexpected errors
        log_error(error, {
            "command": interaction.command.name if interaction.command else "unknown",
            "user_id": interaction.user.id,
            "channel_id": interaction.channel_id,
            "guild_id": interaction.guild_id,
        })
        
        # Send error response
        error_message = "❌ An unexpected error occurred while processing your command."
        
        if interaction.response.is_done():
            await interaction.followup.send(error_message, ephemeral=True)
        else:
            await interaction.response.send_message(error_message, ephemeral=True)
    
    @bot.event
    async def on_error(event: str, *args: Any, **kwargs: Any) -> None:
        """
        Handle general bot errors.
        
        Args:
            event: The event that caused the error
            *args: Event arguments
            **kwargs: Event keyword arguments
        """
        logger = get_logger(__name__)
        
        # Get the current exception
        import sys
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        if exc_value:
            log_error(exc_value, {
                "event": event,
                "args": str(args)[:500],  # Limit length to prevent spam
                "kwargs": str(kwargs)[:500],
            })
        else:
            logger.error("Unknown error in event", event=event)
    
    @bot.event
    async def on_guild_join(guild: discord.Guild) -> None:
        """
        Handle bot joining a new guild.
        
        Args:
            guild: The guild that was joined
        """
        logger = get_logger(__name__)
        logger.info("Bot joined new guild", 
                   guild_id=guild.id, 
                   guild_name=guild.name,
                   member_count=guild.member_count)
        
        # Try to send a welcome message to the system channel
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="👋 Hello! Thanks for adding me!",
                color=discord.Color.green(),
                description="I'm an AI assistant powered by a self-hosted LLM. I can chat, answer questions, and help with various tasks!"
            )
            
            embed.add_field(
                name="🚀 Getting Started",
                value="• Use `/chat <message>` to start a conversation\n"
                      "• Use `/help` to see all available commands\n"
                      "• @mention me anywhere to chat\n"
                      "• Reply to my messages to continue conversations",
                inline=False
            )
            
            embed.add_field(
                name="⚙️ Setup",
                value="Make sure I have permission to:\n"
                      "• Read and send messages\n"
                      "• Use slash commands\n"
                      "• Read message history (for context)",
                inline=False
            )
            
            try:
                await guild.system_channel.send(embed=embed)
            except discord.HTTPException:
                logger.warning("Failed to send welcome message", guild_id=guild.id)
    
    @bot.event
    async def on_guild_remove(guild: discord.Guild) -> None:
        """
        Handle bot being removed from a guild.
        
        Args:
            guild: The guild that was left
        """
        logger = get_logger(__name__)
        logger.info("Bot removed from guild", 
                   guild_id=guild.id, 
                   guild_name=guild.name)
        
        # TODO: Optionally clean up conversation data for this guild
    
    @bot.event
    async def on_member_join(member: discord.Member) -> None:
        """
        Handle new member joining a guild.
        
        Args:
            member: The member that joined
        """
        logger = get_logger(__name__)
        logger.debug("New member joined", 
                    user_id=member.id,
                    guild_id=member.guild.id)
    
    @bot.event
    async def on_message_delete(message: discord.Message) -> None:
        """
        Handle message deletion.
        
        Args:
            message: The message that was deleted
        """
        # Only log if it was one of our messages
        if message.author == bot.user:
            logger = get_logger(__name__)
            logger.debug("Bot message deleted", 
                        message_id=message.id,
                        channel_id=message.channel.id)
    
    @bot.event
    async def on_message_edit(before: discord.Message, after: discord.Message) -> None:
        """
        Handle message editing.
        
        Args:
            before: The message before editing
            after: The message after editing
        """
        # Ignore bot messages and messages with no content change
        if before.author.bot or before.content == after.content:
            return
        
        logger = get_logger(__name__)
        logger.debug("Message edited", 
                    message_id=after.id,
                    user_id=after.author.id,
                    channel_id=after.channel.id)
        
        # TODO: Optionally handle edited messages in conversations
    
    logger.info("Event handlers setup complete")
