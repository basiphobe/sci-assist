"""
Data models for LLM API interactions.

This module defines Pydantic models for structured data exchange
with the LLM API, including request/response models and validation.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from enum import Enum

from pydantic import BaseModel, Field, validator


class MessageRole(str, Enum):
    """Enum for message roles in chat conversations."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """
    A single message in a chat conversation.
    
    This model represents a message that can be sent to or received from
    the LLM API. It includes the role (system, user, assistant) and content.
    
    Attributes:
        role: The role of the message sender
        content: The text content of the message
        name: Optional name for the message sender
        extra_data: Optional metadata for the message
    """
    
    role: MessageRole = Field(
        description="The role of the message sender"
    )
    content: str = Field(
        description="The text content of the message",
        min_length=1,
        max_length=32000  # Reasonable limit for most LLMs
    )
    name: Optional[str] = Field(
        default=None,
        description="Optional name for the message sender",
        max_length=64
    )
    extra_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata for the message"
    )
    
    @validator("content")
    def validate_content(cls, v: str) -> str:
        """Validate message content."""
        if not v.strip():
            raise ValueError("Message content cannot be empty or whitespace only")
        return v.strip()
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class ChatRequest(BaseModel):
    """
    Request model for chat completion API calls.
    
    This model structures the request sent to the LLM API for generating
    chat completions, including all necessary parameters and settings.
    
    Attributes:
        model: The name of the LLM model to use
        messages: List of messages in the conversation
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0 to 2.0)
        top_p: Nucleus sampling parameter
        frequency_penalty: Frequency penalty parameter
        presence_penalty: Presence penalty parameter
        stop: Stop sequences
        stream: Whether to stream the response
    """
    
    model: str = Field(
        description="The name of the LLM model to use"
    )
    messages: List[ChatMessage] = Field(
        description="List of messages in the conversation",
        min_items=1,
        max_items=100  # Reasonable conversation length limit
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Maximum tokens to generate",
        gt=0,
        le=8192
    )
    temperature: Optional[float] = Field(
        default=0.7,
        description="Sampling temperature (0.0 to 2.0)",
        ge=0.0,
        le=2.0
    )
    top_p: Optional[float] = Field(
        default=None,
        description="Nucleus sampling parameter",
        ge=0.0,
        le=1.0
    )
    frequency_penalty: Optional[float] = Field(
        default=None,
        description="Frequency penalty parameter",
        ge=-2.0,
        le=2.0
    )
    presence_penalty: Optional[float] = Field(
        default=None,
        description="Presence penalty parameter", 
        ge=-2.0,
        le=2.0
    )
    stop: Optional[Union[str, List[str]]] = Field(
        default=None,
        description="Stop sequences"
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the response"
    )
    
    @validator("messages")
    def validate_messages(cls, v: List[ChatMessage]) -> List[ChatMessage]:
        """Validate the messages list."""
        if not v:
            raise ValueError("Messages list cannot be empty")
        
        # Ensure we don't have too many consecutive system messages
        system_count = 0
        for msg in v:
            if msg.role == MessageRole.SYSTEM:
                system_count += 1
            else:
                system_count = 0
            
            if system_count > 3:
                raise ValueError("Too many consecutive system messages")
        
        return v


class ChatChoice(BaseModel):
    """
    A single choice from a chat completion response.
    
    Attributes:
        index: The index of this choice
        message: The generated message
        finish_reason: Why the generation stopped
    """
    
    index: int = Field(
        description="The index of this choice"
    )
    message: ChatMessage = Field(
        description="The generated message"
    )
    finish_reason: Optional[Literal["stop", "length", "content_filter", "null"]] = Field(
        default=None,
        description="Why the generation stopped"
    )


class ChatUsage(BaseModel):
    """
    Token usage information from a chat completion.
    
    Attributes:
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: Total number of tokens used
    """
    
    prompt_tokens: int = Field(
        description="Number of tokens in the prompt",
        ge=0
    )
    completion_tokens: int = Field(
        description="Number of tokens in the completion",
        ge=0
    )
    total_tokens: int = Field(
        description="Total number of tokens used",
        ge=0
    )
    
    @validator("total_tokens")
    def validate_total_tokens(cls, v: int, values: Dict[str, Any]) -> int:
        """Validate that total tokens equals prompt + completion."""
        prompt_tokens = values.get("prompt_tokens", 0)
        completion_tokens = values.get("completion_tokens", 0)
        
        if v != prompt_tokens + completion_tokens:
            raise ValueError("Total tokens must equal prompt tokens + completion tokens")
        
        return v


class ChatResponse(BaseModel):
    """
    Response model for chat completion API calls.
    
    This model structures the response received from the LLM API after
    generating a chat completion.
    
    Attributes:
        id: Unique identifier for the completion
        object: Object type (should be "chat.completion")
        created: Unix timestamp of creation
        model: The model used for generation
        choices: List of generated choices
        usage: Token usage information
    """
    
    id: str = Field(
        description="Unique identifier for the completion"
    )
    object: str = Field(
        description="Object type",
        pattern=r"^chat\.completion$"
    )
    created: int = Field(
        description="Unix timestamp of creation"
    )
    model: str = Field(
        description="The model used for generation"
    )
    choices: List[ChatChoice] = Field(
        description="List of generated choices",
        min_items=1
    )
    usage: Optional[ChatUsage] = Field(
        default=None,
        description="Token usage information"
    )
    
    @property
    def content(self) -> str:
        """Get the content of the first choice."""
        if not self.choices:
            return ""
        return self.choices[0].message.content
    
    @property
    def created_datetime(self) -> datetime:
        """Get the creation time as a datetime object."""
        return datetime.fromtimestamp(self.created)


class LLMError(BaseModel):
    """
    Error response from the LLM API.
    
    Attributes:
        error: Error information
        type: Error type
        code: Error code
        message: Human-readable error message
    """
    
    type: str = Field(
        description="Error type"
    )
    code: Optional[str] = Field(
        default=None,
        description="Error code"
    )
    message: str = Field(
        description="Human-readable error message"
    )
    param: Optional[str] = Field(
        default=None,
        description="Parameter that caused the error"
    )


class HealthCheckResponse(BaseModel):
    """
    Response model for health check endpoints.
    
    Attributes:
        status: Health status
        model: Current model name
        timestamp: Response timestamp
        version: API version
    """
    
    status: Literal["healthy", "unhealthy"] = Field(
        description="Health status"
    )
    model: Optional[str] = Field(
        default=None,
        description="Current model name"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Response timestamp"
    )
    version: Optional[str] = Field(
        default=None,
        description="API version"
    )
