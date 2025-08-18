"""
Discord commands for privacy management.
"""

import discord
from discord.ext import commands
from typing import Optional
from datetime import datetime

from .manager import PrivacyManager, UserConsent


class PrivacyCommands(commands.Cog):
    """Discord commands for managing user privacy and data consent."""
    
    def __init__(self, bot: commands.Bot, privacy_manager: PrivacyManager):
        self.bot = bot
        self.privacy_manager = privacy_manager
    
    @discord.app_commands.command(name="privacy", description="Manage your data privacy settings")
    async def privacy_menu(self, interaction: discord.Interaction):
        """Show privacy management menu."""
        embed = discord.Embed(
            title="🔒 Privacy & Data Management",
            description="Manage how your data is handled by the SCI-Assist bot.",
            color=discord.Color.blue()
        )
        
        # Get current consent status
        user_id = interaction.user.id
        consent = self.privacy_manager.get_user_consent(user_id)
        
        if consent:
            status = "✅ Consented" if consent.data_retention_consent else "❌ Not Consented"
            training_status = "✅ Consented" if consent.training_data_consent else "❌ Not Consented"
        else:
            status = "❓ No preference set"
            training_status = "❓ No preference set"
        
        embed.add_field(
            name="Current Data Retention Status",
            value=status,
            inline=False
        )
        
        embed.add_field(
            name="Training Data Usage",
            value=training_status,
            inline=False
        )
        
        embed.add_field(
            name="Data Retention Policy",
            value=f"• Operational data: {self.privacy_manager.policy.operational_days} days\\n"
                  f"• Training data: Only with consent\\n"
                  f"• Automatic cleanup: {'Enabled' if self.privacy_manager.policy.auto_cleanup_enabled else 'Disabled'}",
            inline=False
        )
        
        # Create buttons for privacy actions
        view = PrivacyView(self.privacy_manager, user_id)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.app_commands.command(name="data_export", description="Export your personal data")
    async def data_export(self, interaction: discord.Interaction):
        """Export user's personal data."""
        await interaction.response.defer(ephemeral=True)
        
        # This would implement data export functionality
        embed = discord.Embed(
            title="📥 Data Export",
            description="Your data export has been prepared. In a real implementation, this would generate a secure download link.",
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.app_commands.command(name="delete_data", description="Request deletion of your personal data")
    async def delete_data(self, interaction: discord.Interaction):
        """Request deletion of user's personal data."""
        embed = discord.Embed(
            title="🗑️ Data Deletion Request",
            description="⚠️ **Warning**: This will permanently delete all your conversation history and cannot be undone.\\n\\n"
                       "To confirm deletion, please contact a moderator with your request.",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class PrivacyView(discord.ui.View):
    """Interactive view for privacy management."""
    
    def __init__(self, privacy_manager: PrivacyManager, user_id: int):
        super().__init__(timeout=300)
        self.privacy_manager = privacy_manager
        self.user_id = user_id
    
    @discord.ui.button(label="✅ Consent to Data Retention", style=discord.ButtonStyle.green)
    async def consent_retention(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle consent to data retention."""
        consent = self.privacy_manager.get_user_consent(self.user_id) or UserConsent(user_id=self.user_id)
        consent.data_retention_consent = True
        consent.consent_date = datetime.now()
        
        self.privacy_manager.update_user_consent(consent)
        
        embed = discord.Embed(
            title="✅ Consent Updated",
            description="You have consented to data retention for operational purposes.",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📚 Consent to Training Data", style=discord.ButtonStyle.blurple)
    async def consent_training(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle consent to training data usage."""
        consent = self.privacy_manager.get_user_consent(self.user_id) or UserConsent(user_id=self.user_id)
        consent.training_data_consent = True
        consent.consent_date = datetime.now()
        
        self.privacy_manager.update_user_consent(consent)
        
        embed = discord.Embed(
            title="✅ Training Consent Updated",
            description="You have consented to anonymized use of your conversations for training purposes.",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="❌ Revoke Consent", style=discord.ButtonStyle.red)
    async def revoke_consent(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle consent revocation."""
        consent = self.privacy_manager.get_user_consent(self.user_id) or UserConsent(user_id=self.user_id)
        consent.data_retention_consent = False
        consent.training_data_consent = False
        consent.updated_date = datetime.now()
        
        self.privacy_manager.update_user_consent(consent)
        
        embed = discord.Embed(
            title="❌ Consent Revoked",
            description="Your consent has been revoked. Future conversations will not be stored.",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
