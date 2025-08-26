"""
Streaming response handling for real-time agent communication
"""
from typing import Any, Dict, Optional, AsyncGenerator
from pydantic import BaseModel
from datetime import datetime
import json


class StreamingResponse(BaseModel):
    """A single streaming response chunk"""
    type: str  # "content", "tool_call", "tool_result", "error", "done"
    data: Any
    timestamp: datetime = None
    
    def __init__(self, **data):
        if data.get('timestamp') is None:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)
    
    def to_sse_event(self, event: str = "message") -> str:
        """Convert to Server-Sent Events format"""
        data = {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"
    
    def to_websocket_message(self) -> Dict[str, Any]:
        """Convert to WebSocket message format"""
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }


class ContentChunk(StreamingResponse):
    """Content streaming chunk"""
    type: str = "content"
    
    @classmethod
    def create(cls, content: str, delta: bool = True):
        return cls(data={"content": content, "delta": delta})


class ToolCallChunk(StreamingResponse):
    """Tool call streaming chunk"""
    type: str = "tool_call"
    
    @classmethod
    def create(cls, tool_name: str, arguments: Dict[str, Any], call_id: str):
        return cls(data={
            "name": tool_name,
            "arguments": arguments,
            "id": call_id
        })


class ToolResultChunk(StreamingResponse):
    """Tool result streaming chunk"""
    type: str = "tool_result"
    
    @classmethod
    def create(cls, result: Dict[str, Any], call_id: str):
        return cls(data={
            "result": result,
            "id": call_id
        })


class ErrorChunk(StreamingResponse):
    """Error streaming chunk"""
    type: str = "error"
    
    @classmethod
    def create(cls, error: str, code: str = "unknown"):
        return cls(data={"error": error, "code": code})


class DoneChunk(StreamingResponse):
    """Completion streaming chunk"""
    type: str = "done"
    
    @classmethod
    def create(cls, final_message: Optional[str] = None):
        return cls(data={"final_message": final_message})


class StreamingManager:
    """Manages streaming response formatting and conversion"""
    
    @staticmethod
    async def to_sse_stream(
        response_generator: AsyncGenerator[StreamingResponse, None]
    ) -> AsyncGenerator[str, None]:
        """Convert streaming responses to SSE format"""
        try:
            async for chunk in response_generator:
                yield chunk.to_sse_event()
        except Exception as e:
            error_chunk = ErrorChunk.create(str(e), "stream_error")
            yield error_chunk.to_sse_event()
        finally:
            # Send completion event
            done_chunk = DoneChunk.create()
            yield done_chunk.to_sse_event()
    
    @staticmethod
    async def to_websocket_stream(
        response_generator: AsyncGenerator[StreamingResponse, None]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Convert streaming responses to WebSocket format"""
        try:
            async for chunk in response_generator:
                yield chunk.to_websocket_message()
        except Exception as e:
            error_chunk = ErrorChunk.create(str(e), "stream_error")
            yield error_chunk.to_websocket_message()
        finally:
            # Send completion event
            done_chunk = DoneChunk.create()
            yield done_chunk.to_websocket_message()
    
    @staticmethod
    async def collect_full_response(
        response_generator: AsyncGenerator[StreamingResponse, None]
    ) -> Dict[str, Any]:
        """Collect full response from streaming chunks"""
        content_parts = []
        tool_calls = []
        errors = []
        
        async for chunk in response_generator:
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
            "success": len(errors) == 0
        }