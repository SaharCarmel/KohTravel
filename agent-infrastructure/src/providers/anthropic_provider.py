"""
Anthropic provider implementation for Claude models
"""
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
import anthropic
from anthropic.types import MessageParam, ToolParam
import structlog

from src.providers.base import BaseProvider, ProviderConfig
from src.core.streaming import StreamingResponse, ContentChunk, ToolCallChunk, ToolResultChunk, DoneChunk, ErrorChunk
from src.tools.base import Tool, ToolResult

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
        self.tools = {}  # Will be set by agent
        logger.info("Anthropic provider initialized", model=config.model)
    
    def set_tools(self, tools: Dict[str, Tool]):
        """Set available tools for execution"""
        self.tools = tools
        logger.info("Tools registered with provider", tool_count=len(tools))
    
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
        Production-grade streaming with proper tool execution
        """
        try:
            # Execute complete conversation flow with tool handling
            async for response in self._execute_tool_conversation(
                messages=messages,
                model=model or self.config.model,
                max_tokens=max_tokens or 4096,
                temperature=temperature or 0.0,
                tools=tools,
                **kwargs
            ):
                yield response
                
        except Exception as e:
            logger.error("Streaming completion failed", error=str(e))
            yield ErrorChunk.create(f"Streaming failed: {str(e)}", "anthropic_error")
    
    async def _execute_tool_conversation(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        max_tokens: int,
        temperature: float,
        tools: Optional[List[Tool]] = None,
        max_rounds: int = 3,
        **kwargs
    ) -> AsyncGenerator[StreamingResponse, None]:
        """
        Execute multi-round conversation with proper tool use
        """
        conversation_messages = messages.copy()
        round_count = 0
        
        while round_count < max_rounds:
            round_count += 1
            logger.info("Starting conversation round", round=round_count, total_messages=len(conversation_messages))
            
            # Build API parameters
            api_params = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": self._format_for_anthropic_api(conversation_messages)
            }
            
            # Add system message if present
            system_message = self._extract_system_message(conversation_messages)
            if system_message:
                api_params["system"] = system_message
            
            # Add tools if available
            if tools:
                api_params["tools"] = [self._convert_tool_to_anthropic(tool) for tool in tools]
            
            # Get Claude's response
            response = await self.client.messages.create(**api_params)
            
            # Process response
            text_content = ""
            tool_calls = []
            assistant_content = []
            
            for content_block in response.content:
                if content_block.type == "text":
                    text_content += content_block.text
                    assistant_content.append({
                        "type": "text",
                        "text": content_block.text
                    })
                    # Stream text content
                    yield ContentChunk.create(content_block.text, delta=False)
                    
                elif content_block.type == "tool_use":
                    tool_call = {
                        "id": content_block.id,
                        "name": content_block.name,
                        "input": content_block.input
                    }
                    tool_calls.append(tool_call)
                    assistant_content.append({
                        "type": "tool_use",
                        "id": content_block.id,
                        "name": content_block.name,
                        "input": content_block.input
                    })
                    
                    # Stream tool call
                    yield ToolCallChunk.create(
                        tool_name=content_block.name,
                        arguments=content_block.input,
                        call_id=content_block.id
                    )
            
            # Add assistant message to conversation
            conversation_messages.append({
                "role": "assistant",
                "content": assistant_content
            })
            
            # If no tools used, conversation is complete
            if not tool_calls:
                yield DoneChunk.create(text_content)
                return
            
            # Execute tools
            tool_results = await self._execute_tools_parallel(tool_calls, kwargs.get("context", {}))
            
            # Stream tool results and add to conversation
            tool_result_content = []
            for tool_call, result in zip(tool_calls, tool_results):
                yield ToolResultChunk.create(
                    result=result.dict(),
                    call_id=tool_call["id"]
                )
                
                tool_result_content.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call["id"],
                    "content": result.content
                })
            
            # Add tool results as user message for next round
            conversation_messages.append({
                "role": "user",
                "content": tool_result_content
            })
        
        # Max rounds reached
        logger.warning("Maximum conversation rounds reached", rounds=max_rounds)
        yield ErrorChunk.create("Conversation reached maximum rounds", "max_rounds_exceeded")
    
    async def _execute_tools_parallel(
        self, 
        tool_calls: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> List[ToolResult]:
        """Execute multiple tools in parallel with proper error handling"""
        import asyncio
        
        async def execute_single_tool(tool_call: Dict[str, Any]) -> ToolResult:
            tool_name = tool_call["name"] 
            tool_input = tool_call["input"]
            
            if tool_name not in self.tools:
                return ToolResult(
                    success=False,
                    content=f"Tool '{tool_name}' not available",
                    error="tool_not_found"
                )
            
            tool = self.tools[tool_name]
            
            try:
                logger.info("Executing tool", tool=tool_name, input=tool_input)
                result = await tool.safe_execute(tool_input, context)
                logger.info("Tool completed", tool=tool_name, success=result.success)
                return result
                
            except Exception as e:
                logger.error("Tool execution error", tool=tool_name, error=str(e))
                return ToolResult(
                    success=False,
                    content=f"Tool execution failed: {str(e)}",
                    error=str(e)
                )
        
        # Execute all tools concurrently
        tasks = [execute_single_tool(call) for call in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to ToolResult errors
        final_results = []
        for result in results:
            if isinstance(result, Exception):
                final_results.append(ToolResult(
                    success=False,
                    content=f"Tool execution exception: {str(result)}",
                    error=str(result)
                ))
            else:
                final_results.append(result)
        
        return final_results
    
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
    
    def _format_for_anthropic_api(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format messages for Anthropic API (exclude system messages)"""
        formatted_messages = []
        
        for msg in messages:
            if msg["role"] in ["user", "assistant"]:
                formatted_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        return formatted_messages
    
    def _extract_system_message(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """Extract and format system message"""
        for msg in messages:
            if msg["role"] == "system":
                content = msg["content"]
                if isinstance(content, str):
                    return content
                elif isinstance(content, list):
                    # Handle structured content
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block["text"])
                        elif isinstance(block, str):
                            text_parts.append(block)
                    return "".join(text_parts)
        return None
    
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