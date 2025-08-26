"""
Core Agent class for managing AI conversations and tool execution
"""
from typing import Dict, List, Any, Optional, AsyncGenerator, Callable
import asyncio
import structlog
from pydantic import BaseModel

from src.core.conversation import Conversation, Message, MessageRole
from src.core.streaming import StreamingResponse
from src.providers.base import BaseProvider
from src.tools.base import Tool, ToolResult

logger = structlog.get_logger(__name__)


class AgentConfig(BaseModel):
    """Agent configuration"""
    name: str
    system_prompt: str
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4096
    temperature: float = 0.0
    enabled_tools: List[str] = []


class Agent:
    """
    Core agent class that orchestrates conversations with AI providers and tool execution
    """
    
    def __init__(
        self,
        config: AgentConfig,
        provider: BaseProvider,
        tools: Optional[Dict[str, Tool]] = None,
        context_providers: Optional[List[Callable]] = None
    ):
        self.config = config
        self.provider = provider
        self.tools = tools or {}
        self.context_providers = context_providers or []
        self.conversations: Dict[str, Conversation] = {}
        
        logger.info("Agent initialized", agent_name=config.name, tools=list(self.tools.keys()))
    
    def register_tool(self, name: str, tool: Tool) -> None:
        """Register a tool with the agent"""
        if name in self.config.enabled_tools or not self.config.enabled_tools:
            self.tools[name] = tool
            logger.info("Tool registered", tool_name=name)
        else:
            logger.warning("Tool not enabled in config", tool_name=name)
    
    def register_context_provider(self, provider: Callable) -> None:
        """Register a context provider function"""
        self.context_providers.append(provider)
        logger.info("Context provider registered")
    
    async def get_context(self, session_id: str, **kwargs) -> Dict[str, Any]:
        """Gather context from all registered providers"""
        context = {}
        
        for provider in self.context_providers:
            try:
                provider_context = await provider(session_id=session_id, **kwargs)
                context.update(provider_context)
            except Exception as e:
                logger.error("Context provider failed", error=str(e))
        
        return context
    
    def get_conversation(self, session_id: str) -> Conversation:
        """Get or create conversation for session"""
        if session_id not in self.conversations:
            self.conversations[session_id] = Conversation(
                session_id=session_id,
                system_prompt=self.config.system_prompt
            )
        return self.conversations[session_id]
    
    async def send_message(
        self,
        session_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AsyncGenerator[StreamingResponse, None]:
        """
        Send a message to the agent and get streaming response
        """
        conversation = self.get_conversation(session_id)
        
        # Add user message to conversation
        conversation.add_message(Message(
            role=MessageRole.USER,
            content=message
        ))
        
        # Gather context
        full_context = await self.get_context(session_id, **kwargs)
        if context:
            full_context.update(context)
        
        # Build messages for provider with context injection
        messages = self._build_messages_with_context(conversation, full_context)
        
        # Stream response from provider
        async for chunk in self.provider.stream_completion(
            messages=messages,
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            tools=list(self.tools.values()) if self.tools else None
        ):
            # Handle tool calls
            if chunk.type == "tool_call":
                yield StreamingResponse(type="tool_call_start", data=chunk.data)
                
                try:
                    tool_result = await self._execute_tool(chunk.data, session_id, full_context)
                    yield StreamingResponse(type="tool_call_result", data=tool_result.dict())
                    
                    # Add tool result to conversation
                    conversation.add_message(Message(
                        role=MessageRole.TOOL,
                        content=tool_result.content,
                        tool_call_id=chunk.data.get("id")
                    ))
                    
                except Exception as e:
                    error_result = ToolResult(
                        success=False,
                        content=f"Tool execution failed: {str(e)}",
                        error=str(e)
                    )
                    yield StreamingResponse(type="tool_call_error", data=error_result.dict())
                    logger.error("Tool execution failed", error=str(e), tool=chunk.data.get("name"))
            
            # Handle regular content
            elif chunk.type == "content":
                yield chunk
            
            # Handle completion
            elif chunk.type == "done":
                # Add assistant response to conversation
                if hasattr(chunk, 'final_message') and chunk.final_message:
                    conversation.add_message(Message(
                        role=MessageRole.ASSISTANT,
                        content=chunk.final_message
                    ))
                yield chunk
    
    def _build_messages_with_context(
        self, 
        conversation: Conversation, 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build message list with context injection"""
        messages = []
        
        # System message with context
        system_prompt = conversation.system_prompt
        if context:
            context_str = self._format_context(context)
            system_prompt = f"{system_prompt}\n\n{context_str}"
        
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # Add conversation messages
        for message in conversation.messages:
            messages.append({
                "role": message.role.value,
                "content": message.content
            })
        
        return messages
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary into prompt-friendly string"""
        if not context:
            return ""
        
        context_parts = []
        for key, value in context.items():
            if isinstance(value, (dict, list)):
                context_parts.append(f"{key.upper()}:\n{str(value)}")
            else:
                context_parts.append(f"{key.upper()}: {value}")
        
        return "CONTEXT:\n" + "\n\n".join(context_parts)
    
    async def _execute_tool(
        self, 
        tool_call: Dict[str, Any], 
        session_id: str,
        context: Dict[str, Any]
    ) -> ToolResult:
        """Execute a tool call"""
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("arguments", {})
        
        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                content=f"Tool '{tool_name}' not found",
                error=f"Unknown tool: {tool_name}"
            )
        
        tool = self.tools[tool_name]
        
        try:
            # Add session context to tool execution
            tool_context = {
                "session_id": session_id,
                "agent_name": self.config.name,
                **context
            }
            
            result = await tool.execute(tool_args, tool_context)
            logger.info("Tool executed successfully", tool=tool_name, session=session_id)
            return result
            
        except Exception as e:
            logger.error("Tool execution error", tool=tool_name, error=str(e))
            return ToolResult(
                success=False,
                content=f"Tool execution failed: {str(e)}",
                error=str(e)
            )
    
    def clear_conversation(self, session_id: str) -> None:
        """Clear conversation history for session"""
        if session_id in self.conversations:
            del self.conversations[session_id]
            logger.info("Conversation cleared", session_id=session_id)
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for session"""
        conversation = self.conversations.get(session_id)
        if not conversation:
            return []
        
        return [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in conversation.messages
        ]