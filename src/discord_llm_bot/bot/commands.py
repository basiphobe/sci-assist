"""
Discord slash commands and text commands for the LLM bot.

This module implements all the commands that users can use to interact
with the bot, including chat commands, conversation management, and
utility functions.
"""

from typing import Optional
from datetime import datetime

import discord
from discord.ext import commands
from discord import app_commands

from discord_llm_bot.utils.logging import get_logger, log_function_call
from discord_llm_bot.utils.exceptions import ConversationError
from discord_llm_bot.privacy.manager import UserConsent


class ChatCommands(commands.Cog):
    """Chat-related commands for the LLM bot."""
    
    def __init__(self, bot) -> None:
        """Initialize the chat commands cog."""
        self.bot = bot
        self.logger = get_logger(__name__)
    
    @app_commands.command(name="chat", description="Start a conversation with the AI")
    @app_commands.describe(message="Your message to the AI")
    async def chat(self, interaction: discord.Interaction, message: str) -> None:
        """
        Start or continue a conversation with the AI.
        
        Args:
            interaction: Discord slash command interaction
            message: The user's message to send to the AI
        """
        log_function_call("chat_command", user_id=interaction.user.id, message_length=len(message))
        
        await interaction.response.defer(thinking=True)
        
        try:
            if not self.bot.conversation_manager:
                raise ConversationError("Conversation manager not available")
            
            # Get or create conversation
            conversation_id = await self.bot.conversation_manager.get_or_create_conversation(
                user_id=interaction.user.id,
                channel_id=interaction.channel_id,
                guild_id=interaction.guild_id,
            )
            
            # Add user message
            await self.bot.conversation_manager.add_message(
                conversation_id=conversation_id,
                content=message,
                role="user",
                extra_data={
                    "discord_user_id": interaction.user.id,
                    "discord_username": str(interaction.user),
                    "command": "chat",
                }
            )
            
            # Generate response
            response = await self.bot.conversation_manager.generate_response(
                conversation_id=conversation_id
            )
            
            # Send response
            chunks = self.bot._split_message(response)
            
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await interaction.followup.send(chunk)
                else:
                    await interaction.followup.send(chunk)
            
            # Add bot response to conversation
            await self.bot.conversation_manager.add_message(
                conversation_id=conversation_id,
                content=response,
                role="assistant",
                extra_data={
                    "discord_user_id": self.bot.user.id if self.bot.user else None,
                    "discord_username": str(self.bot.user) if self.bot.user else "Bot",
                    "command": "chat",
                }
            )
            
        except Exception as e:
            self.logger.error("Error in chat command", error=str(e), user_id=interaction.user.id)
            await interaction.followup.send("❌ Sorry, I encountered an error processing your message.")
    
    @app_commands.command(name="reset", description="Reset your conversation history")
    async def reset_conversation(self, interaction: discord.Interaction) -> None:
        """
        Reset the conversation history for this user/channel.
        
        Args:
            interaction: Discord slash command interaction
        """
        log_function_call("reset_command", user_id=interaction.user.id)
        
        try:
            if not self.bot.conversation_manager:
                raise ConversationError("Conversation manager not available")
            
            await self.bot.conversation_manager.reset_conversation(
                user_id=interaction.user.id,
                channel_id=interaction.channel_id,
                guild_id=interaction.guild_id,
            )
            
            await interaction.response.send_message(
                "✅ Your conversation history has been reset!",
                ephemeral=True
            )
            
        except Exception as e:
            self.logger.error("Error in reset command", error=str(e), user_id=interaction.user.id)
            await interaction.response.send_message(
                "❌ Sorry, I couldn't reset your conversation.",
                ephemeral=True
            )
    
    @app_commands.command(name="context", description="Show your current conversation context")
    async def show_context(self, interaction: discord.Interaction) -> None:
        """
        Show the current conversation context and statistics.
        
        Args:
            interaction: Discord slash command interaction
        """
        log_function_call("context_command", user_id=interaction.user.id)
        
        try:
            if not self.bot.conversation_manager:
                raise ConversationError("Conversation manager not available")
            
            context_info = await self.bot.conversation_manager.get_conversation_context(
                user_id=interaction.user.id,
                channel_id=interaction.channel_id,
                guild_id=interaction.guild_id,
            )
            
            if not context_info:
                await interaction.response.send_message(
                    "You don't have any conversation history yet. Start chatting with `/chat`!",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="🧠 Conversation Context",
                color=discord.Color.blue(),
                description="Here's your current conversation status"
            )
            
            embed.add_field(
                name="📊 Statistics",
                value=f"**Messages:** {context_info['message_count']}\n"
                      f"**Tokens:** {context_info['total_tokens']}\n"
                      f"**Started:** <t:{int(context_info['created_at'].timestamp())}:R>",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Context Window",
                value=f"**Used:** {context_info['context_tokens']}/{self.bot.config.conversation.context_window_tokens}\n"
                      f"**Usage:** {context_info['context_tokens']/self.bot.config.conversation.context_window_tokens*100:.1f}%",
                inline=True
            )
            
            if context_info['last_message']:
                embed.add_field(
                    name="💬 Last Message",
                    value=f"<t:{int(context_info['last_message'].timestamp())}:R>",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error("Error in context command", error=str(e), user_id=interaction.user.id)
            await interaction.response.send_message(
                "❌ Sorry, I couldn't retrieve your conversation context.",
                ephemeral=True
            )


class UtilityCommands(commands.Cog):
    """Utility commands for the LLM bot."""
    
    def __init__(self, bot) -> None:
        """Initialize the utility commands cog."""
        self.bot = bot
        self.logger = get_logger(__name__)
    
    @app_commands.command(name="help", description="Show help information")
    async def help_command(self, interaction: discord.Interaction) -> None:
        """
        Show help information about the bot and its commands.
        
        Args:
            interaction: Discord slash command interaction
        """
        embed = discord.Embed(
            title="🤖 Discord LLM Bot Help",
            color=discord.Color.green(),
            description="I'm an AI assistant powered by a self-hosted LLM. Here's how to use me:"
        )
        
        embed.add_field(
            name="💬 Starting Conversations",
            value="• Use `/chat <message>` to start a conversation\n"
                  "• @mention me anywhere to chat\n"
                  "• Reply to my messages to continue the conversation\n"
                  "• Send me a DM for private conversations",
            inline=False
        )
        
        embed.add_field(
            name="🎛️ Commands",
            value="• `/chat <message>` - Chat with the AI\n"
                  "• `/reset` - Reset your conversation history\n"
                  "• `/context` - Show your conversation stats\n"
                  "• `/help` - Show this help message",
            inline=False
        )
        
        embed.add_field(
            name="🧠 Memory & Context",
            value="• I remember our conversation history\n"
                  "• Each user/channel has separate conversations\n"
                  "• Context is managed automatically within token limits\n"
                  "• Use `/reset` to start fresh anytime",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Features",
            value="• Powered by self-hosted LLM\n"
                  "• Persistent conversation memory\n"
                  "• Smart context management\n"
                  "• Multi-user support",
            inline=False
        )
        
        embed.set_footer(text="Need more help? Contact the bot administrator.")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="status", description="Show bot status and health")
    async def status(self, interaction: discord.Interaction) -> None:
        """
        Show bot status and health information.
        
        Args:
            interaction: Discord slash command interaction
        """
        try:
            # Check LLM connectivity
            llm_status = "✅ Connected"
            if self.bot.llm_client:
                try:
                    await self.bot.llm_client.health_check()
                except Exception:
                    llm_status = "❌ Disconnected"
            else:
                llm_status = "❌ Not initialized"
            
            # Check database connectivity
            db_status = "✅ Connected"
            if self.bot.db_manager:
                try:
                    await self.bot.db_manager.health_check()
                except Exception:
                    db_status = "❌ Disconnected"
            else:
                db_status = "❌ Not initialized"
            
            embed = discord.Embed(
                title="🔍 Bot Status",
                color=discord.Color.blue(),
                description="Current bot health and status"
            )
            
            embed.add_field(
                name="🤖 Bot Status",
                value=f"**Discord:** ✅ Connected\n"
                      f"**LLM:** {llm_status}\n"
                      f"**Database:** {db_status}",
                inline=True
            )
            
            embed.add_field(
                name="📊 Statistics",
                value=f"**Guilds:** {len(self.bot.guilds)}\n"
                      f"**Users:** {sum(guild.member_count or 0 for guild in self.bot.guilds)}\n"
                      f"**Latency:** {self.bot.latency*1000:.0f}ms",
                inline=True
            )
            
            embed.add_field(
                name="⚙️ Configuration",
                value=f"**LLM Model:** {self.bot.config.llm.model_name}\n"
                      f"**Max Tokens:** {self.bot.config.llm.max_tokens}\n"
                      f"**Temperature:** {self.bot.config.llm.temperature}",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error("Error in status command", error=str(e))
            await interaction.response.send_message(
                "❌ Sorry, I couldn't retrieve status information.",
                ephemeral=True
            )


class PrivacyCommands(commands.Cog):
    """Privacy and data management commands."""
    
    def __init__(self, bot) -> None:
        """Initialize the privacy commands cog."""
        self.bot = bot
        self.logger = get_logger(__name__)
    
    @app_commands.command(name="privacy", description="Manage your data privacy settings")
    async def privacy_menu(self, interaction: discord.Interaction) -> None:
        """Show privacy management menu."""
        log_function_call("privacy_command", user_id=interaction.user.id)
        
        if not self.bot.conversation_manager or not hasattr(self.bot.conversation_manager, 'privacy_manager'):
            await interaction.response.send_message(
                "❌ Privacy management is not available right now. Please try again later.",
                ephemeral=True
            )
            return
        
        privacy_manager = self.bot.conversation_manager.privacy_manager
        
        embed = discord.Embed(
            title="🔒 Privacy & Data Management",
            description="Manage how your data is handled by the SCI-Assist bot.",
            color=discord.Color.blue()
        )
        
        # Get current consent status
        user_id = interaction.user.id
        consent = privacy_manager.get_user_consent(user_id)
        
        if consent:
            status = "✅ Consented" if consent.data_retention_consent else "❌ Not Consented"
            training_status = "✅ Consented" if consent.training_data_consent else "❌ Not Consented"
            consent_date = consent.consent_date.strftime("%Y-%m-%d") if consent.consent_date else "Unknown"
        else:
            status = "❓ No preference set (default: no storage)"
            training_status = "❓ No preference set (default: no training use)"
            consent_date = "Never"
        
        embed.add_field(
            name="Current Data Retention Status",
            value=f"{status}\n*Last updated: {consent_date}*",
            inline=False
        )
        
        embed.add_field(
            name="Training Data Usage",
            value=f"{training_status}\n*Anonymized data for bot improvements*",
            inline=False
        )
        
        embed.add_field(
            name="Data Retention Policy",
            value=f"• Operational data: {privacy_manager.policy.operational_days} days\n"
                  f"• Training data: Only with consent\n"
                  f"• Automatic cleanup: {'Enabled' if privacy_manager.policy.auto_cleanup_enabled else 'Disabled'}",
            inline=False
        )
        
        embed.add_field(
            name="Important Notes",
            value="• Without consent, conversations are not stored but bot still helps you\n"
                  "• Training data is fully anonymized (no personal info)\n"
                  "• You can change preferences anytime",
            inline=False
        )
        
        # Create buttons for privacy actions
        view = PrivacyView(privacy_manager, user_id)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="data_export", description="Export your personal data")
    async def data_export(self, interaction: discord.Interaction) -> None:
        """Export user's personal data."""
        log_function_call("data_export_command", user_id=interaction.user.id)
        
        await interaction.response.defer(ephemeral=True)
        
        if not self.bot.conversation_manager or not hasattr(self.bot.conversation_manager, 'privacy_manager'):
            await interaction.followup.send(
                "❌ Privacy management is not available right now.",
                ephemeral=True
            )
            return
        
        # For now, just provide information about data export
        embed = discord.Embed(
            title="📥 Data Export Request",
            description="Your data export request has been received.",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="What's Included",
            value="• All stored conversation messages\n"
                  "• Your consent preferences\n"
                  "• Account creation and update dates",
            inline=False
        )
        
        embed.add_field(
            name="Next Steps",
            value="In a full implementation, this would:\n"
                  "• Generate a secure download link\n"
                  "• Email you the export file\n"
                  "• Log the export request",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="delete_data", description="Request deletion of your personal data")
    async def delete_data(self, interaction: discord.Interaction) -> None:
        """Request deletion of user's personal data."""
        log_function_call("delete_data_command", user_id=interaction.user.id)
        
        embed = discord.Embed(
            title="🗑️ Data Deletion Request",
            description="⚠️ **Warning**: This will permanently delete all your conversation history and cannot be undone.",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="What Will Be Deleted",
            value="• All your stored messages\n"
                  "• Your conversation history\n"
                  "• Your consent preferences",
            inline=False
        )
        
        embed.add_field(
            name="What Will NOT Be Deleted",
            value="• Anonymized training data (no personal info)\n"
                  "• Your Discord account (external to bot)",
            inline=False
        )
        
        embed.add_field(
            name="To Proceed",
            value="Please contact a server moderator or administrator to process this request. "
                  "Include your Discord ID in the request for verification.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class PrivacyView(discord.ui.View):
    """Interactive view for privacy management."""
    
    def __init__(self, privacy_manager, user_id: int):
        super().__init__(timeout=300)
        self.privacy_manager = privacy_manager
        self.user_id = user_id
    
    @discord.ui.button(label="✅ Consent to Data Storage", style=discord.ButtonStyle.green)
    async def consent_retention(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle consent to data retention."""
        consent = self.privacy_manager.get_user_consent(self.user_id) or UserConsent(user_id=self.user_id)
        consent.data_retention_consent = True
        consent.consent_date = datetime.now()
        
        self.privacy_manager.update_user_consent(consent)
        
        embed = discord.Embed(
            title="✅ Consent Updated",
            description="You have consented to data retention for operational purposes.\n\n"
                       "**What this means:**\n"
                       "• Your conversations will be stored for up to 7 days\n"
                       "• This helps the bot maintain context in ongoing conversations\n"
                       "• Data is automatically deleted after the retention period",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📚 Consent to Training Use", style=discord.ButtonStyle.blurple)
    async def consent_training(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle consent to training data usage."""
        consent = self.privacy_manager.get_user_consent(self.user_id) or UserConsent(user_id=self.user_id)
        consent.training_data_consent = True
        consent.consent_date = datetime.now()
        
        self.privacy_manager.update_user_consent(consent)
        
        embed = discord.Embed(
            title="✅ Training Consent Updated",
            description="You have consented to anonymized use of your conversations for training.\n\n"
                       "**What this means:**\n"
                       "• Your messages help improve the bot's responses\n"
                       "• All personal information is removed/anonymized\n"
                       "• Only conversation patterns are used, not personal data",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="❌ Revoke All Consent", style=discord.ButtonStyle.red)
    async def revoke_consent(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle consent revocation."""
        consent = self.privacy_manager.get_user_consent(self.user_id) or UserConsent(user_id=self.user_id)
        consent.data_retention_consent = False
        consent.training_data_consent = False
        consent.updated_date = datetime.now()
        
        self.privacy_manager.update_user_consent(consent)
        
        embed = discord.Embed(
            title="❌ Consent Revoked",
            description="Your consent has been revoked.\n\n"
                       "**What this means:**\n"
                       "• Future conversations will not be stored\n"
                       "• The bot will still respond to help you\n"
                       "• No conversation context will be maintained\n"
                       "• Existing data will be cleaned up according to retention policy",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="ℹ️ Learn More", style=discord.ButtonStyle.secondary)
    async def learn_more(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show more information about privacy."""
        embed = discord.Embed(
            title="ℹ️ Privacy Information",
            description="Learn more about how your data is handled.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Data We Collect",
            value="• Messages you send to the bot\n"
                  "• Discord username and display name\n"
                  "• Channel and server information\n"
                  "• Message timestamps",
            inline=False
        )
        
        embed.add_field(
            name="How We Use It",
            value="• Providing conversational context\n"
                  "• Improving bot responses (anonymized)\n"
                  "• Technical debugging and monitoring",
            inline=False
        )
        
        embed.add_field(
            name="Your Rights",
            value="• Right to consent or refuse data storage\n"
                  "• Right to export your data\n"
                  "• Right to delete your data\n"
                  "• Right to change preferences anytime",
            inline=False
        )
        
        embed.add_field(
            name="Security",
            value="• Data stored locally on secure servers\n"
                  "• Automatic cleanup of old data\n"
                  "• No sharing with third parties\n"
                  "• Training data fully anonymized",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup_commands(bot) -> None:
    """
    Set up all bot commands.
    
    Args:
        bot: The Discord bot instance
    """
    logger = get_logger(__name__)
    logger.debug("Setting up bot commands")
    
    # Add command cogs
    await bot.add_cog(ChatCommands(bot))
    await bot.add_cog(UtilityCommands(bot))
    await bot.add_cog(PrivacyCommands(bot))
    
    # Log all registered commands for debugging
    all_commands = bot.tree.get_commands()
    logger.info(f"Total commands registered: {len(all_commands)}")
    for cmd in all_commands:
        logger.info(f"Registered command: {cmd.name} - {cmd.description}")
    
    logger.info("Bot commands setup complete")
