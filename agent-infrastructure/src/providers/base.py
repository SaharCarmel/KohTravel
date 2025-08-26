"""
Base provider interface for different LLM providers
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel

from ..core.streaming import StreamingResponse
from ..tools.base import Tool


class ProviderConfig(BaseModel):
    """Base configuration for LLM providers"""
    api_key: str
    model: str = "default"
    base_url: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3


class BaseProvider(ABC):
    """
    Abstract base class for LLM providers
    """
    
    def __init__(self, config: ProviderConfig):
        self.config = config
    
    @abstractmethod
    async def stream_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Tool]] = None,
        **kwargs
    ) -> AsyncGenerator[StreamingResponse, None]:
        """
        Stream a completion response from the provider
        
        Args:
            messages: List of conversation messages
            model: Model to use (overrides config default)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            tools: Available tools for the model to use
            **kwargs: Additional provider-specific parameters
            
        Yields:
            StreamingResponse chunks
        """
        pass
    
    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Tool]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a complete response from the provider
        
        Args:
            messages: List of conversation messages
            model: Model to use (overrides config default)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            tools: Available tools for the model to use
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Complete response dictionary
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models for this provider"""
        pass
    
    def validate_model(self, model: str) -> bool:
        """Validate if model is available"""
        return model in self.get_available_models()
    
    def get_tool_schema(self, tool: Tool) -> Dict[str, Any]:
        """Convert tool to provider-specific schema"""
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.get_parameters_schema()
        }