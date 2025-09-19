"""
Session model for Agent OS

This model stores conversation sessions with message history:
- Session management with UUID identifiers
- Conversation history as JSON array
- Relationship to agents and user contexts
- Activity tracking for cleanup
"""
from sqlalchemy import String, JSON, ForeignKey, DateTime, Index, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from src.database.base import Base
import uuid

if TYPE_CHECKING:
    from .agent import AgentModel
    from .user_context import UserAgentContextModel


class SessionModel(Base):
    """
    Conversation session with message history

    This model represents a conversation session between a user and an agent.
    It stores the complete conversation history and maintains relationships
    to both the agent and user context for proper scoping and personalization.

    Key Features:
    - UUID-based session identifiers for security
    - JSON storage for conversation history with message metadata
    - Foreign key relationships to agent and user context
    - Activity tracking for session cleanup and monitoring
    - Flexible session metadata storage
    """
    __tablename__ = "sessions"

    # Session UUID
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique session identifier (UUID)"
    )

    # Foreign key to agent
    agent_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the agent handling this session"
    )

    # User ID from calling application
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="User identifier from the calling application"
    )

    # Optional user context reference
    user_context_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("user_agent_context.id", ondelete="SET NULL"),
        nullable=True,
        doc="Reference to user context if personalization is enabled"
    )

    # Conversation history as JSON array
    conversation_history: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        doc="Array of conversation messages with metadata"
    )

    # Session metadata for application-specific data
    session_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Application-specific session metadata"
    )

    # Session title for UI/organization
    title: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Optional session title for organization"
    )

    # Session status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this session is active"
    )

    # Last activity tracking
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Timestamp of last activity in this session"
    )

    # Message count for quick reference
    message_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of messages in this session"
    )

    # Relationships
    agent: Mapped["AgentModel"] = relationship(
        "AgentModel",
        back_populates="sessions",
        doc="The agent handling this session"
    )

    user_context: Mapped[Optional["UserAgentContextModel"]] = relationship(
        "UserAgentContextModel",
        back_populates="sessions",
        doc="User context for personalization (optional)"
    )

    # Indexes for performance
    __table_args__ = (
        Index("ix_session_agent_user", "agent_id", "user_id"),
        Index("ix_session_last_active", "last_active_at"),
        Index("ix_session_user_id", "user_id"),
        Index("ix_session_agent_id", "agent_id"),
        Index("ix_session_active", "is_active"),
        Index("ix_session_user_active", "user_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<SessionModel(id={self.id}, agent={self.agent_id}, user={self.user_id})>"

    @property
    def session_identifier(self) -> str:
        """Get session identifier in format agent_id/user_id/session_id"""
        return f"{self.agent_id}/{self.user_id}/{self.id}"

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a message to the conversation history

        Args:
            role: Message role (user, assistant, system, tool)
            content: Message content
            metadata: Optional message metadata
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }

        if self.conversation_history is None:
            self.conversation_history = []

        self.conversation_history.append(message)
        self.message_count = len(self.conversation_history)
        self.last_active_at = datetime.now(timezone.utc)

    def get_messages(self, limit: Optional[int] = None, role_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get messages from conversation history

        Args:
            limit: Optional limit on number of messages to return
            role_filter: Optional filter by message role

        Returns:
            List of message dictionaries
        """
        if not self.conversation_history:
            return []

        messages = self.conversation_history

        if role_filter:
            messages = [msg for msg in messages if msg.get("role") == role_filter]

        if limit:
            messages = messages[-limit:]

        return messages

    def clear_history(self) -> None:
        """Clear conversation history"""
        self.conversation_history = []
        self.message_count = 0
        self.last_active_at = datetime.now(timezone.utc)

    def update_activity(self) -> None:
        """Update last activity timestamp"""
        self.last_active_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary representation"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "user_context_id": self.user_context_id,
            "title": self.title,
            "is_active": self.is_active,
            "message_count": self.message_count,
            "session_metadata": self.session_metadata,
            "last_active_at": self.last_active_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }