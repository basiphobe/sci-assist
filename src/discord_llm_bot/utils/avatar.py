"""
Bot avatar management utilities.

This module provides functions to update the bot's avatar programmatically.
Useful for dynamic avatar changes or automated setup.
"""

import aiohttp
from pathlib import Path
from typing import Optional

import discord
from discord_llm_bot.utils.logging import get_logger

logger = get_logger(__name__)


async def update_bot_avatar(
    bot: discord.Client,
    avatar_path: str,
    force_update: bool = False
) -> bool:
    """
    Update the bot's avatar from a local file.
    
    Args:
        bot: The Discord bot client
        avatar_path: Path to the avatar image file
        force_update: Whether to update even if avatar exists
        
    Returns:
        True if avatar was updated, False otherwise
        
    Example:
        ```python
        success = await update_bot_avatar(bot, "assets/logo.png")
        if success:
            print("Avatar updated successfully!")
        ```
    """
    try:
        avatar_file = Path(avatar_path)
        
        if not avatar_file.exists():
            logger.warning(f"Avatar file not found: {avatar_path}")
            return False
        
        # Check if bot already has an avatar (unless forcing update)
        if not force_update and bot.user.avatar:
            logger.info("Bot already has an avatar, skipping update")
            return False
        
        # Read the image file
        with open(avatar_file, 'rb') as f:
            avatar_data = f.read()
        
        # Update the avatar
        await bot.user.edit(avatar=avatar_data)
        logger.info(f"Successfully updated bot avatar from {avatar_path}")
        return True
        
    except discord.HTTPException as e:
        logger.error(f"Failed to update avatar - Discord API error: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to update avatar: {e}")
        return False


async def download_and_set_avatar(
    bot: discord.Client, 
    url: str,
    save_path: Optional[str] = None
) -> bool:
    """
    Download an image from URL and set it as bot avatar.
    
    Args:
        bot: The Discord bot client
        url: URL of the image to download
        save_path: Optional path to save the downloaded image
        
    Returns:
        True if successful, False otherwise
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Failed to download image: HTTP {response.status}")
                    return False
                
                avatar_data = await response.read()
        
        # Save locally if path provided
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(avatar_data)
            logger.info(f"Saved avatar to {save_path}")
        
        # Set as bot avatar
        await bot.user.edit(avatar=avatar_data)
        logger.info(f"Successfully updated bot avatar from {url}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to download and set avatar: {e}")
        return False
