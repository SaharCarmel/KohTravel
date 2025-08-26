"""
Conversation management for agent interactions
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
import uuid


class MessageRole(str, Enum):
    """Message roles in conversation"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """A single message in a conversation"""
    id: str = None
    role: MessageRole
    content: str
    timestamp: datetime = None
    tool_call_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
    
    def __init__(self, **data):
        if data.get('id') is None:
            data['id'] = str(uuid.uuid4())
        if data.get('timestamp') is None:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class Conversation(BaseModel):
    """A conversation thread with message history"""
    session_id: str
    system_prompt: str
    messages: List[Message] = []
    created_at: datetime = None
    updated_at: datetime = None
    metadata: Dict[str, Any] = {}
    
    def __init__(self, **data):
        if data.get('created_at') is None:
            data['created_at'] = datetime.utcnow()
        if data.get('updated_at') is None:
            data['updated_at'] = datetime.utcnow()
        super().__init__(**data)
    
    def add_message(self, message: Message) -> None:
        """Add a message to the conversation"""
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
    
    def get_recent_messages(self, limit: int = 10) -> List[Message]:
        """Get recent messages from conversation"""
        return self.messages[-limit:]
    
    def get_messages_by_role(self, role: MessageRole) -> List[Message]:
        """Get all messages with specific role"""
        return [msg for msg in self.messages if msg.role == role]
    
    def clear_messages(self) -> None:
        """Clear all messages from conversation"""
        self.messages = []
        self.updated_at = datetime.utcnow()
    
    def get_context_summary(self, max_messages: int = 20) -> str:
        """Get a summary of recent conversation context"""
        recent_messages = self.get_recent_messages(max_messages)
        
        if not recent_messages:
            return "No previous conversation context."
        
        context_lines = []
        for msg in recent_messages:
            role_prefix = {
                MessageRole.USER: "User:",
                MessageRole.ASSISTANT: "Assistant:",
                MessageRole.TOOL: "Tool Result:",
                MessageRole.SYSTEM: "System:"
            }.get(msg.role, "Unknown:")
            
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            context_lines.append(f"{role_prefix} {content}")
        
        return "\n".join(context_lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary"""
        return {
            "session_id": self.session_id,
            "system_prompt": self.system_prompt,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message_count": len(self.messages),
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "tool_call_id": msg.tool_call_id,
                    "metadata": msg.metadata
                }
                for msg in self.messages
            ],
            "metadata": self.metadata
        }