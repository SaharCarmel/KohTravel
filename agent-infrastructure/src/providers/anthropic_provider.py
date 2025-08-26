"""
Anthropic provider implementation for Claude models
"""
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
import anthropic
from anthropic.types import MessageParam, ToolParam
import structlog

from src.providers.base import BaseProvider, ProviderConfig
from src.core.streaming import StreamingResponse, ContentChunk, ToolCallChunk, DoneChunk, ErrorChunk
from src.tools.base import Tool

logger = structlog.get_logger(__name__)


class AnthropicConfig(ProviderConfig):
    """Anthropic-specific configuration"""
    model: str = "claude-3-5-sonnet-20241022"
    base_url: Optional[str] = None


class AnthropicProvider(BaseProvider):
    """
    Anthropic Claude provider implementation
    """
    
    AVAILABLE_MODELS = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022", 
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307"
    ]
    
    def __init__(self, config: AnthropicConfig):
        super().__init__(config)
        self.client = anthropic.AsyncAnthropic(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries
        )
        logger.info("Anthropic provider initialized", model=config.model)
    
    async def stream_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Tool]] = None,
        **kwargs
    ) -> AsyncGenerator[StreamingResponse, None]:
        """Stream completion from Anthropic"""
        
        # Prepare parameters
        model = model or self.config.model
        max_tokens = max_tokens or 4096
        temperature = temperature or 0.0
        
        # Convert messages to Anthropic format
        anthropic_messages = self._convert_messages(messages)
        
        # Convert tools to Anthropic format
        anthropic_tools = None
        if tools:
            anthropic_tools = [self._convert_tool_to_anthropic(tool) for tool in tools]
        
        try:
            # Create streaming request
            stream_params = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": anthropic_messages,
                "stream": True,
                **kwargs
            }
            
            if anthropic_tools:
                stream_params["tools"] = anthropic_tools
            
            # Start streaming
            current_content = ""
            current_tool_calls = []
            
            async with self.client.messages.stream(**stream_params) as stream:
                async for event in stream:
                    # Handle content deltas
                    if hasattr(event, 'delta') and hasattr(event.delta, 'text'):
                        content = event.delta.text
                        current_content += content
                        yield ContentChunk.create(content, delta=True)
                    
                    # Handle tool use
                    elif hasattr(event, 'delta') and hasattr(event.delta, 'partial_json'):
                        # Tool call in progress
                        continue
                    
                    # Handle tool use start
                    elif (hasattr(event, 'content_block') and 
                          hasattr(event.content_block, 'type') and 
                          event.content_block.type == 'tool_use'):
                        tool_call = {
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "arguments": event.content_block.input
                        }
                        current_tool_calls.append(tool_call)
                        yield ToolCallChunk.create(
                            tool_name=tool_call["name"],
                            arguments=tool_call["arguments"],
                            call_id=tool_call["id"]
                        )
            
            # Send completion
            yield DoneChunk.create(final_message=current_content)
            
        except Exception as e:
            logger.error("Anthropic streaming error", error=str(e), model=model)
            yield ErrorChunk.create(f"Streaming failed: {str(e)}", "anthropic_error")
    
    async def complete(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Tool]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Get complete response from Anthropic"""
        
        # Collect streaming response
        content_parts = []
        tool_calls = []
        errors = []
        
        async for chunk in self.stream_completion(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
            **kwargs
        ):
            if chunk.type == "content":
                content_parts.append(chunk.data.get("content", ""))
            elif chunk.type == "tool_call":
                tool_calls.append(chunk.data)
            elif chunk.type == "error":
                errors.append(chunk.data)
        
        return {
            "content": "".join(content_parts),
            "tool_calls": tool_calls,
            "errors": errors,
            "success": len(errors) == 0,
            "model": model or self.config.model
        }
    
    def get_available_models(self) -> List[str]:
        """Get available Anthropic models"""
        return self.AVAILABLE_MODELS.copy()
    
    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[MessageParam]:
        """Convert generic messages to Anthropic format"""
        anthropic_messages = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            # Skip system messages (handled separately in Anthropic)
            if role == "system":
                continue
            
            # Convert role mapping
            if role == "tool":
                # Tool results are handled differently in Anthropic
                continue
            
            anthropic_messages.append({
                "role": role,
                "content": content
            })
        
        return anthropic_messages
    
    def _convert_tool_to_anthropic(self, tool: Tool) -> ToolParam:
        """Convert generic tool to Anthropic tool format"""
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.get_parameters_schema()
        }
    
    def _extract_system_message(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """Extract system message from message list"""
        for msg in messages:
            if msg["role"] == "system":
                return msg["content"]
        return None