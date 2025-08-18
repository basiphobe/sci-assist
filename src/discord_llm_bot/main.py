"""
Main entry point for the Discord LLM Bot.

This module provides the main function and CLI interface for starting
the Discord bot. It handles configuration loading, logging setup,
and graceful shutdown handling.
"""

import asyncio
import signal
import sys
from typing import Optional

import structlog

from discord_llm_bot.config import load_config, AppConfig
from discord_llm_bot.utils.logging import setup_logging, get_logger
from discord_llm_bot.utils.exceptions import ConfigurationError
from discord_llm_bot.bot.client import DiscordLLMBot


async def create_bot(config: AppConfig) -> DiscordLLMBot:
    """
    Create and configure the Discord bot instance.
    
    Args:
        config: Application configuration
        
    Returns:
        Configured DiscordLLMBot instance
        
    Raises:
        ConfigurationError: If bot cannot be configured
    """
    logger = get_logger(__name__)
    
    try:
        logger.info("Creating Discord bot instance", 
                   llm_url=config.llm.api_url,
                   database_url=config.database.url)
        
        bot = DiscordLLMBot(config)
        await bot.setup()
        
        logger.info("Bot instance created successfully")
        return bot
        
    except Exception as e:
        logger.error("Failed to create bot instance", error=str(e))
        raise ConfigurationError(
            "Failed to create bot instance",
            context={"error": str(e)},
            original_error=e
        )


async def run_bot(config: AppConfig) -> None:
    """
    Run the Discord bot with proper error handling and shutdown.
    
    Args:
        config: Application configuration
        
    Raises:
        ConfigurationError: If bot cannot be started
    """
    logger = get_logger(__name__)
    bot: Optional[DiscordLLMBot] = None
    
    shutdown_event = asyncio.Event()
    
    try:
        # Create bot instance
        bot = await create_bot(config)
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum: int, frame) -> None:
            logger.info("Received shutdown signal", signal=signum)
            shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start the bot
        logger.info("Starting Discord bot", 
                   token_prefix=config.discord.token[:10] + "...")
        
        # Start bot in background and wait for shutdown signal
        bot_task = asyncio.create_task(bot.start(config.discord.token))
        shutdown_task = asyncio.create_task(shutdown_event.wait())
        
        # Wait for either bot to finish or shutdown signal
        done, pending = await asyncio.wait(
            [bot_task, shutdown_task], 
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel any remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error("Bot encountered fatal error", error=str(e))
        raise
    finally:
        if bot:
            logger.info("Cleaning up bot resources")
            try:
                # Give the bot a shorter time to shut down gracefully
                await asyncio.wait_for(bot.close(), timeout=5.0)
                logger.info("Bot shutdown completed successfully")
            except asyncio.TimeoutError:
                logger.warning("Bot shutdown timed out after 5 seconds, forcing close")
            except Exception as e:
                logger.error("Error during bot shutdown", error=str(e))


async def main_async() -> None:
    """
    Async main function that handles the complete bot lifecycle.
    
    This function:
    1. Loads configuration
    2. Sets up logging
    3. Creates and runs the bot
    4. Handles shutdown gracefully
    """
    try:
        # Load configuration
        config = load_config()
        
        # Set up logging
        setup_logging(config.logging)
        logger = get_logger(__name__)
        
        logger.info("Discord LLM Bot starting up",
                   version="0.1.0",
                   debug_mode=config.debug)
        
        # Run the bot
        await run_bot(config)
        
    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        logger = get_logger(__name__)
        logger.info("Discord LLM Bot shutdown complete")


def main() -> None:
    """
    Main entry point for the Discord LLM Bot.
    
    This function is called when the bot is started from the command line
    or when imported as a module. It sets up the async environment and
    runs the main async function.
    
    Example:
        Command line usage:
        ```bash
        discord-llm-bot
        ```
        
        Programmatic usage:
        ```python
        from discord_llm_bot.main import main
        main()
        ```
    """
    try:
        # Check Python version
        if sys.version_info < (3, 11):
            print("Error: Python 3.11 or higher is required", file=sys.stderr)
            sys.exit(1)
        
        # Run the async main function
        asyncio.run(main_async())
        
    except KeyboardInterrupt:
        print("\nBot shutdown requested", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error during startup: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
