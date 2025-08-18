"""Test configuration and utilities."""

import pytest
import asyncio
from typing import AsyncGenerator

from discord_llm_bot.config import AppConfig, DatabaseConfig, LLMConfig, DiscordConfig, ConversationConfig, LoggingConfig


@pytest.fixture
def test_config() -> AppConfig:
    """Create a test configuration."""
    config = AppConfig()
    
    # Override with test-specific settings
    config.database = DatabaseConfig(url="sqlite:///:memory:", echo=False)
    config.discord = DiscordConfig(token="test_token_" + "x" * 50)
    config.llm = LLMConfig(
        api_url="http://localhost:8000/test",
        model_name="test-model",
        max_tokens=100,
        temperature=0.0,
    )
    config.conversation = ConversationConfig(
        max_history=10,
        context_window_tokens=1000,
        auto_cleanup_days=1,
    )
    config.logging = LoggingConfig(level="DEBUG", format="text")
    
    return config


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "id": "test-completion-123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a test response from the LLM."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 15,
            "total_tokens": 25
        }
    }
