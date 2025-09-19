"""
User agent context model for Agent OS

This model stores user-specific agent customizations including:
- Custom prompt additions
- User preferences (language, tone, etc.)
- Context metadata for personalization
"""
from sqlalchemy import String, Text, JSON, ForeignKey, UniqueConstraint, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Dict, Any, Optional, TYPE_CHECKING, List
from src.database.base import Base

if TYPE_CHECKING:
    from .agent import AgentModel
    from .session import SessionModel


class UserAgentContextModel(Base):
    """
    User-specific agent context and preferences

    This model enables personalization of agents on a per-user basis
    while maintaining the shared agent configuration. It supports:
    - Custom prompt additions that augment the base system prompt
    - User preferences for behavior customization
    - Flexible metadata storage for application-specific context

    Key Features:
    - Foreign key relationship to AgentModel
    - Unique constraint per (agent_id, user_id) pair
    - JSON storage for flexible preference and metadata structure
    - Optimized indexes for user and agent lookups
    """
    __tablename__ = "user_agent_context"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Auto-incrementing primary key"
    )

    # Foreign key to agent
    agent_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the agent this context belongs to"
    )

    # User ID from calling application (e.g., KohTravel user ID)
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="User identifier from the calling application"
    )

    # User-specific prompt modifications
    custom_prompt_addons: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Additional prompt text to append to base system prompt"
    )

    # User preferences as JSON: {language: "en", tone: "friendly", etc.}
    user_preferences: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="User preferences as JSON object (language, tone, format preferences)"
    )

    # Additional user context metadata
    context_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Application-specific context metadata"
    )

    # User settings for this agent
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="User-specific agent settings and configuration overrides"
    )

    # Whether this context is active
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        doc="Whether this user context is active"
    )

    # Relationships
    agent: Mapped["AgentModel"] = relationship(
        "AgentModel",
        back_populates="user_contexts",
        doc="The agent this context belongs to"
    )

    sessions: Mapped[List["SessionModel"]] = relationship(
        "SessionModel",
        back_populates="user_context",
        cascade="all, delete-orphan",
        doc="Sessions using this user context"
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("agent_id", "user_id", name="uq_user_agent_context"),
        Index("ix_user_context_agent_user", "agent_id", "user_id"),
        Index("ix_user_context_user_id", "user_id"),
        Index("ix_user_context_agent_id", "agent_id"),
        Index("ix_user_context_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<UserAgentContextModel(id={self.id}, agent={self.agent_id}, user={self.user_id})>"

    @property
    def context_identifier(self) -> str:
        """Get context identifier in format agent_id/user_id"""
        return f"{self.agent_id}/{self.user_id}"

    def get_effective_prompt_additions(self) -> str:
        """Get the effective prompt additions for this user context"""
        if not self.is_active:
            return ""
        return self.custom_prompt_addons or ""

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a specific user preference by key"""
        if not self.user_preferences:
            return default
        return self.user_preferences.get(key, default)

    def set_preference(self, key: str, value: Any) -> None:
        """Set a user preference (call save to persist)"""
        if self.user_preferences is None:
            self.user_preferences = {}
        self.user_preferences[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert user context to dictionary representation"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "custom_prompt_addons": self.custom_prompt_addons,
            "user_preferences": self.user_preferences,
            "context_metadata": self.context_metadata,
            "settings": self.settings,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }