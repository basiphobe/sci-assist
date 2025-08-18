"""
Discord LLM Bot - A modern Discord bot that interfaces with self-hosted LLMs.

This package provides a complete Discord bot implementation that can connect to
any self-hosted Large Language Model with an HTTP API, maintaining conversation
history and context across interactions.

Key Features:
- Full Discord integration with slash commands
- LLM API client with retry logic and error handling  
- Persistent conversation memory with context management
- Modern Python patterns with full type hints
- Comprehensive test coverage
- Production-ready with Docker support

Example:
    Basic usage:
    
    ```python
    from discord_llm_bot.main import main
    
    if __name__ == "__main__":
        main()
    ```
"""

__version__ = "0.1.0"

# Only import main function to avoid circular dependencies during development
def main():
    """Main entry point for the Discord LLM Bot."""
    from discord_llm_bot.main import main as _main
    return _main()

__all__ = ["main", "__version__"]
