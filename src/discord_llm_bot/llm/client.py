"""
LLM API client for communicating with self-hosted language models.

This module provides a robust HTTP client for interacting with LLM APIs,
with support for retries, rate limiting, and proper error handling.
The client is designed to work with OpenAI-compatible APIs but can be
adapted for custom LLM endpoints.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
import json

import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from discord_llm_bot.config import LLMConfig
from discord_llm_bot.utils.logging import (
    get_logger, 
    log_function_call, 
    log_error,
    log_http_request,
    log_http_response,
    log_llm_interaction,
    log_operation_timing,
    generate_correlation_id,
)
from discord_llm_bot.utils.exceptions import LLMAPIError
from discord_llm_bot.llm.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    LLMError,
    HealthCheckResponse,
    MessageRole,
)


class LLMClient:
    """
    HTTP client for LLM API communication.
    
    This client handles all communication with the self-hosted LLM API,
    including request/response serialization, error handling, retries,
    and rate limiting.
    
    Key Features:
    - Automatic retries with exponential backoff
    - Request/response validation with Pydantic
    - Comprehensive error handling and logging
    - Health check capabilities
    - Support for streaming responses (future enhancement)
    - Rate limiting and timeout management
    
    Attributes:
        config: LLM configuration settings
        session: Async HTTP session for API calls
    """
    
    def __init__(self, config: LLMConfig) -> None:
        """
        Initialize the LLM client.
        
        Args:
            config: LLM configuration containing API URL, model settings, etc.
        """
        self.config = config
        self.logger = get_logger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        self._closed = False
        
        log_function_call(
            "LLMClient.__init__",
            api_url=config.api_url,
            model_name=config.model_name,
            max_tokens=config.max_tokens,
        )
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """
        Ensure that we have an active HTTP session.
        
        Returns:
            The HTTP session
            
        Raises:
            LLMAPIError: If the client has been closed
        """
        if self._closed:
            raise LLMAPIError("LLM client has been closed")
        
        if self.session is None or self.session.closed:
            # Set up headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Discord-LLM-Bot/0.1.0",
            }
            
            # Add API key if configured
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            # Create session with timeout
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
                raise_for_status=False,  # We'll handle status codes manually
            )
            
            self.logger.debug("Created new HTTP session for LLM client")
        
        return self.session
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    )
    async def generate_chat_completion(
        self,
        messages: List[ChatMessage],
        **kwargs: Any,
    ) -> ChatResponse:
        """
        Generate a chat completion using the LLM API.
        
        This method sends a chat completion request to the LLM API and returns
        the structured response. It includes automatic retries for transient
        failures and comprehensive error handling.
        
        Args:
            messages: List of conversation messages
            **kwargs: Additional parameters to override defaults
            
        Returns:
            The chat completion response from the LLM
            
        Raises:
            LLMAPIError: If the API call fails or returns an error
            
        Example:
            ```python
            messages = [
                ChatMessage(role=MessageRole.USER, content="Hello, how are you?")
            ]
            response = await llm_client.generate_chat_completion(messages)
            print(response.content)
            ```
        """
        correlation_id = generate_correlation_id()
        
        log_function_call(
            "generate_chat_completion",
            message_count=len(messages),
            model=self.config.model_name,
            correlation_id=correlation_id,
        )
        
        # Build the request
        request_data = ChatRequest(
            model=self.config.model_name,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            top_p=kwargs.get("top_p"),
            frequency_penalty=kwargs.get("frequency_penalty"),
            presence_penalty=kwargs.get("presence_penalty"),
            stop=kwargs.get("stop"),
            stream=kwargs.get("stream", False),
        )
        
        # Log the request
        request_dict = request_data.dict(exclude_none=True)
        log_http_request(
            method="POST",
            url=self.config.api_url,
            headers={"Content-Type": "application/json"},
            body=request_dict,
            service="llm",
            correlation_id=correlation_id
        )
        
        start_time = time.time()
        
        try:
            session = await self._ensure_session()
            
            # Make the API request
            async with session.post(
                self.config.api_url,
                json=request_dict,
            ) as response:
                response_time_ms = (time.time() - start_time) * 1000
                response_text = await response.text()
                response_size = len(response_text.encode('utf-8'))
                
                # Log the response
                log_http_response(
                    status_code=response.status,
                    response_time_ms=response_time_ms,
                    response_size=response_size,
                    service="llm",
                    correlation_id=correlation_id
                )
                
                # Check for successful response
                if response.status == 200:
                    try:
                        response_data = json.loads(response_text)
                        chat_response = ChatResponse(**response_data)
                        
                        # Log successful LLM interaction with token usage
                        log_llm_interaction(
                            model=self.config.model_name,
                            prompt_tokens=chat_response.usage.prompt_tokens if chat_response.usage else None,
                            completion_tokens=chat_response.usage.completion_tokens if chat_response.usage else None,
                            total_tokens=chat_response.usage.total_tokens if chat_response.usage else None,
                            response_time_ms=response_time_ms,
                            correlation_id=correlation_id,
                            finish_reason=chat_response.choices[0].finish_reason if chat_response.choices else None,
                            message_count=len(messages),
                        )
                        
                        self.logger.debug(
                            "Successfully generated chat completion",
                            tokens_used=chat_response.usage.total_tokens if chat_response.usage else None,
                            finish_reason=chat_response.choices[0].finish_reason if chat_response.choices else None,
                            correlation_id=correlation_id,
                        )
                        
                        return chat_response
                        
                    except (json.JSONDecodeError, ValueError) as e:
                        error_msg = "Failed to parse LLM API response"
                        log_http_response(
                            status_code=response.status,
                            response_time_ms=response_time_ms,
                            error=error_msg,
                            service="llm",
                            correlation_id=correlation_id
                        )
                        raise LLMAPIError(
                            error_msg,
                            context={
                                "status_code": response.status,
                                "response_text": response_text[:500],
                                "correlation_id": correlation_id,
                            },
                            original_error=e,
                        )
                
                # Handle error responses
                else:
                    await self._handle_error_response(
                        response.status, 
                        response_text, 
                        response_time_ms,
                        correlation_id
                    )
        
        except aiohttp.ClientError as e:
            response_time_ms = (time.time() - start_time) * 1000
            error_msg = "Failed to communicate with LLM API"
            log_http_response(
                status_code=0,
                response_time_ms=response_time_ms,
                error=f"{error_msg}: {str(e)}",
                service="llm",
                correlation_id=correlation_id
            )
            raise LLMAPIError(
                error_msg,
                context={
                    "api_url": self.config.api_url,
                    "error_type": type(e).__name__,
                    "correlation_id": correlation_id,
                },
                original_error=e,
            )
        except asyncio.TimeoutError as e:
            response_time_ms = (time.time() - start_time) * 1000
            error_msg = "LLM API request timed out"
            log_http_response(
                status_code=0,
                response_time_ms=response_time_ms,
                error=error_msg,
                service="llm",
                correlation_id=correlation_id
            )
            raise LLMAPIError(
                error_msg,
                context={
                    "timeout": self.config.timeout,
                    "api_url": self.config.api_url,
                    "correlation_id": correlation_id,
                },
                original_error=e,
            )
    
    async def _handle_error_response(
        self, 
        status_code: int, 
        response_text: str,
        response_time_ms: float,
        correlation_id: str
    ) -> None:
        """
        Handle error responses from the LLM API.
        
        Args:
            status_code: HTTP status code
            response_text: Response body text
            response_time_ms: Response time in milliseconds
            correlation_id: Request correlation ID
            
        Raises:
            LLMAPIError: Always raises with appropriate error details
        """
        log_http_response(
            status_code=status_code,
            response_time_ms=response_time_ms,
            error=f"HTTP {status_code} error",
            service="llm",
            correlation_id=correlation_id
        )
        
        try:
            # Try to parse error response
            error_data = json.loads(response_text)
            
            if "error" in error_data:
                error_info = error_data["error"]
                if isinstance(error_info, dict):
                    llm_error = LLMError(**error_info)
                    error_message = llm_error.message
                else:
                    error_message = str(error_info)
            else:
                error_message = response_text
                
        except (json.JSONDecodeError, ValueError):
            error_message = response_text[:500] if response_text else "Unknown error"
        
        # Map status codes to specific error types
        if status_code == 400:
            error_type = "Bad Request - Invalid parameters"
        elif status_code == 401:
            error_type = "Unauthorized - Invalid API key"
        elif status_code == 403:
            error_type = "Forbidden - Access denied"
        elif status_code == 404:
            error_type = "Not Found - Invalid endpoint"
        elif status_code == 429:
            error_type = "Rate Limited - Too many requests"
        elif status_code >= 500:
            error_type = "Server Error - LLM service unavailable"
        else:
            error_type = f"HTTP Error {status_code}"
        
        raise LLMAPIError(
            f"LLM API error: {error_type}",
            context={
                "status_code": status_code,
                "error_message": error_message,
                "api_url": self.config.api_url,
            },
        )
    
    async def health_check(self) -> HealthCheckResponse:
        """
        Perform a health check on the LLM API.
        
        This method sends a simple request to verify that the LLM API
        is accessible and responding correctly.
        
        Returns:
            Health check response
            
        Raises:
            LLMAPIError: If the health check fails
            
        Example:
            ```python
            try:
                health = await llm_client.health_check()
                print(f"LLM is {health.status}")
            except LLMAPIError:
                print("LLM is not accessible")
            ```
        """
        log_function_call("health_check")
        
        try:
            # Try a simple chat completion with minimal content
            test_messages = [
                ChatMessage(
                    role=MessageRole.USER,
                    content="Hello"
                )
            ]
            
            response = await self.generate_chat_completion(
                messages=test_messages,
                max_tokens=5,
                temperature=0.0,
            )
            
            self.logger.debug("Health check passed")
            
            return HealthCheckResponse(
                status="healthy",
                model=self.config.model_name,
            )
            
        except Exception as e:
            self.logger.warning("Health check failed", error=str(e))
            
            return HealthCheckResponse(
                status="unhealthy",
                model=self.config.model_name,
            )
    
    async def close(self) -> None:
        """
        Close the HTTP session and clean up resources.
        
        This method should be called when shutting down the application
        to ensure proper cleanup of HTTP connections.
        """
        if not self._closed:
            self.logger.debug("Closing LLM client")
            
            if self.session and not self.session.closed:
                await self.session.close()
            
            self._closed = True
            self.logger.debug("LLM client closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
