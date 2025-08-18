"""
Logging configuration and utilities for the Discord LLM Bot.

This module provides centralized logging setup with support for both
structured JSON logging (for production) and human-readable text logging
(for development). It integrates with structlog for structured logging
and rich for beautiful console output.

The logging configuration is based on the application config and provides
consistent logging across all modules with proper formatting and context.

Enhanced features:
- HTTP request/response logging for Discord and LLM APIs
- Performance timing and metrics
- Request correlation IDs for tracing
- Service-specific loggers
- Error tracking and debugging utilities
"""

import logging
import sys
import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

import structlog
from rich.console import Console
from rich.logging import RichHandler

from discord_llm_bot.config import LoggingConfig


def setup_logging(config: LoggingConfig) -> None:
    """
    Set up application logging based on configuration.
    
    This function configures the logging system with either JSON structured
    logging for production or rich text logging for development. It sets up
    both the standard library logging and structlog for consistent output.
    
    Args:
        config: Logging configuration settings
        
    Example:
        ```python
        from discord_llm_bot.config import load_config
        from discord_llm_bot.utils.logging import setup_logging
        
        app_config = load_config()
        setup_logging(app_config.logging)
        
        logger = structlog.get_logger()
        logger.info("Application started", version="1.0.0")
        ```
    """
    # Clear any existing handlers
    logging.getLogger().handlers.clear()
    
    # Set up the root logger level
    logging.getLogger().setLevel(config.level)
    
    if config.format == "json":
        # Production-style JSON logging
        _setup_json_logging(config)
    else:
        # Development-style rich text logging
        _setup_rich_logging(config)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.CallsiteParameterAdder(
                parameters=[structlog.processors.CallsiteParameter.FILENAME,
                           structlog.processors.CallsiteParameter.LINENO]
            ),
            _structlog_processor if config.format == "json" else _rich_processor,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, config.level)
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure external library loggers to reduce noise
    configure_external_loggers()


def _setup_json_logging(config: LoggingConfig) -> None:
    """Set up structured JSON logging for production."""
    formatter = logging.Formatter(
        fmt='{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%SZ"
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(config.level)
    
    logging.getLogger().addHandler(handler)


def _setup_rich_logging(config: LoggingConfig) -> None:
    """Set up rich text logging for development."""
    console = Console(force_terminal=True, width=120)
    
    handler = RichHandler(
        console=console,
        show_time=True,
        show_level=True,
        show_path=True,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
    )
    
    handler.setLevel(config.level)
    logging.getLogger().addHandler(handler)


def _structlog_processor(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> str:
    """Process structlog events for JSON output."""
    import json
    
    # Format the event as JSON
    return json.dumps(event_dict, default=str)


def _rich_processor(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> str:
    """Process structlog events for rich text output."""
    # Extract the main message
    message = event_dict.pop("event", "")
    
    # Add context if present
    if event_dict:
        context_items = []
        for key, value in event_dict.items():
            if key not in {"timestamp", "level", "filename", "lineno"}:
                context_items.append(f"{key}={value}")
        
        if context_items:
            message += f" ({', '.join(context_items)})"
    
    return message


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a configured logger instance.
    
    This function returns a structlog BoundLogger that's properly configured
    with the application's logging settings. It provides a consistent interface
    for logging throughout the application.
    
    Args:
        name: Optional logger name (defaults to calling module)
        
    Returns:
        Configured structlog BoundLogger instance
        
    Example:
        ```python
        logger = get_logger(__name__)
        logger.info("Processing message", user_id=12345, message_length=150)
        ```
    """
    return structlog.get_logger(name)


def log_function_call(func_name: str, **kwargs: Any) -> None:
    """
    Log function call with parameters.
    
    Utility function for logging function calls with their parameters.
    Useful for debugging and tracing execution flow.
    
    Args:
        func_name: Name of the function being called
        **kwargs: Function parameters to log
        
    Example:
        ```python
        def process_message(user_id: int, content: str) -> None:
            log_function_call("process_message", user_id=user_id, content=content[:50])
            # ... function implementation
        ```
    """
    logger = get_logger()
    logger.debug("Function called", function=func_name, **kwargs)


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an error with context information.
    
    Utility function for consistent error logging with optional context.
    Automatically includes exception type and message.
    
    Args:
        error: The exception that occurred
        context: Additional context information
        
    Example:
        ```python
        try:
            # Some operation
            pass
        except ValueError as e:
            log_error(e, {"user_id": user.id, "operation": "parse_message"})
            raise
        ```
    """
    logger = get_logger()
    error_context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    
    if context:
        error_context.update(context)
    
    logger.error("Exception occurred", **error_context)


# Enhanced logging utilities for API monitoring and debugging

def generate_correlation_id() -> str:
    """Generate a unique correlation ID for tracking requests."""
    return str(uuid.uuid4())[:8]


def get_service_logger(service_name: str) -> structlog.BoundLogger:
    """
    Get a service-specific logger with consistent naming.
    
    Args:
        service_name: Name of the service (e.g., 'discord', 'llm', 'database')
        
    Returns:
        Logger bound with service context
    """
    logger = get_logger(f"service.{service_name}")
    return logger.bind(service=service_name)


def log_http_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Union[str, Dict[str, Any]]] = None,
    service: str = "unknown",
    correlation_id: Optional[str] = None
) -> None:
    """
    Log HTTP request details.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        headers: Request headers (sensitive headers will be masked)
        body: Request body (will be truncated if too long)
        service: Service name (discord, llm, etc.)
        correlation_id: Optional correlation ID for request tracking
    """
    logger = get_service_logger(service)
    
    # Parse URL to separate domain and path for better logging
    parsed_url = urlparse(url)
    
    # Mask sensitive headers
    safe_headers = {}
    if headers:
        for key, value in headers.items():
            if any(sensitive in key.lower() for sensitive in ['authorization', 'token', 'key', 'secret']):
                safe_headers[key] = f"***{value[-4:] if len(value) > 4 else '***'}"
            else:
                safe_headers[key] = value
    
    # Truncate body if too long
    safe_body = body
    if isinstance(body, str) and len(body) > 1000:
        safe_body = body[:1000] + "... (truncated)"
    elif isinstance(body, dict):
        safe_body = {k: (v if len(str(v)) <= 100 else f"{str(v)[:100]}... (truncated)") 
                    for k, v in body.items()}
    
    logger.info(
        "HTTP request initiated",
        method=method,
        host=parsed_url.netloc,
        path=parsed_url.path,
        headers=safe_headers,
        body=safe_body,
        correlation_id=correlation_id or "none"
    )


def log_http_response(
    status_code: int,
    response_time_ms: float,
    response_size: Optional[int] = None,
    error: Optional[str] = None,
    service: str = "unknown",
    correlation_id: Optional[str] = None
) -> None:
    """
    Log HTTP response details.
    
    Args:
        status_code: HTTP status code
        response_time_ms: Response time in milliseconds
        response_size: Response size in bytes
        error: Error message if request failed
        service: Service name (discord, llm, etc.)
        correlation_id: Optional correlation ID for request tracking
    """
    logger = get_service_logger(service)
    
    log_level = "info"
    if status_code >= 400:
        log_level = "error" if status_code >= 500 else "warning"
    
    log_data = {
        "status_code": status_code,
        "response_time_ms": round(response_time_ms, 2),
        "correlation_id": correlation_id or "none"
    }
    
    if response_size is not None:
        log_data["response_size_bytes"] = response_size
    
    if error:
        log_data["error"] = error
    
    message = f"HTTP response received"
    if error:
        message = f"HTTP request failed"
    
    getattr(logger, log_level)(message, **log_data)


@contextmanager
def log_operation_timing(operation_name: str, **context):
    """
    Context manager to log operation timing.
    
    Args:
        operation_name: Name of the operation being timed
        **context: Additional context to include in logs
    """
    logger = get_logger()
    correlation_id = context.pop('correlation_id', generate_correlation_id())
    
    start_time = time.time()
    logger.info(
        f"Starting {operation_name}",
        operation=operation_name,
        correlation_id=correlation_id,
        **context
    )
    
    try:
        yield correlation_id
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Completed {operation_name}",
            operation=operation_name,
            duration_ms=round(duration_ms, 2),
            correlation_id=correlation_id,
            status="success",
            **context
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Failed {operation_name}",
            operation=operation_name,
            duration_ms=round(duration_ms, 2),
            correlation_id=correlation_id,
            status="error",
            error_type=type(e).__name__,
            error_message=str(e),
            **context
        )
        raise


def log_discord_event(event_type: str, **context):
    """
    Log Discord events with consistent formatting.
    
    Args:
        event_type: Type of Discord event (message, interaction, etc.)
        **context: Event-specific context
    """
    logger = get_service_logger("discord")
    logger.info(
        f"Discord event: {event_type}",
        event_type=event_type,
        **context
    )


def log_llm_interaction(
    model: str,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    response_time_ms: Optional[float] = None,
    **context
):
    """
    Log LLM API interactions with token usage and timing.
    
    Args:
        model: Model name used
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        total_tokens: Total tokens used
        response_time_ms: Response time in milliseconds
        **context: Additional context
    """
    logger = get_service_logger("llm")
    
    log_data = {
        "model": model,
        **context
    }
    
    if prompt_tokens is not None:
        log_data["prompt_tokens"] = prompt_tokens
    if completion_tokens is not None:
        log_data["completion_tokens"] = completion_tokens
    if total_tokens is not None:
        log_data["total_tokens"] = total_tokens
    if response_time_ms is not None:
        log_data["response_time_ms"] = round(response_time_ms, 2)
    
    logger.info("LLM interaction completed", **log_data)


def log_conversation_event(
    event_type: str,
    conversation_id: int,
    user_id: int,
    **context
):
    """
    Log conversation-related events.
    
    Args:
        event_type: Type of conversation event
        conversation_id: Database conversation ID
        user_id: User ID
        **context: Additional context
    """
    logger = get_service_logger("conversation")
    logger.info(
        f"Conversation event: {event_type}",
        event_type=event_type,
        conversation_id=conversation_id,
        user_id=user_id,
        **context
    )


def log_database_operation(
    operation: str,
    table: str,
    duration_ms: Optional[float] = None,
    rows_affected: Optional[int] = None,
    **context
):
    """
    Log database operations.
    
    Args:
        operation: Database operation (SELECT, INSERT, etc.)
        table: Database table name
        duration_ms: Operation duration in milliseconds
        rows_affected: Number of rows affected
        **context: Additional context
    """
    logger = get_service_logger("database")
    
    log_data = {
        "operation": operation,
        "table": table,
        **context
    }
    
    if duration_ms is not None:
        log_data["duration_ms"] = round(duration_ms, 2)
    if rows_affected is not None:
        log_data["rows_affected"] = rows_affected
    
    logger.debug("Database operation", **log_data)


def configure_external_loggers():
    """
    Configure logging levels for external libraries to reduce noise.
    """
    # Reduce Discord.py logging noise
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    logging.getLogger('discord.gateway').setLevel(logging.INFO)
    
    # Reduce HTTP client logging noise
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    # SQLAlchemy logging
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    
    # Keep only important aiosqlite logs
    logging.getLogger('aiosqlite').setLevel(logging.WARNING)
