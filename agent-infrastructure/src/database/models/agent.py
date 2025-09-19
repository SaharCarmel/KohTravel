"""
Agent database model for Agent OS

This model stores agent configuration and metadata, supporting:
- Multi-tenant architecture with app_name scoping
- Flexible tool configuration via JSON
- System prompt management
- Model parameter configuration
"""
from sqlalchemy import String, Text, JSON, UniqueConstraint, Index, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from src.database.base import Base

if TYPE_CHECKING:
    from .user_context import UserAgentContextModel
    from .session import SessionModel


class AgentModel(Base):
    """
    Agent configuration stored in database

    This model represents an AI agent with its configuration, system prompt,
    and tool definitions. Agents are scoped by application (app_name) to
    support multi-tenant architecture.

    Key Features:
    - Composite unique constraint on (app_name, name) for multi-tenancy
    - JSON storage for flexible tool configuration
    - Relationship management for user contexts and sessions
    - Proper indexing for performance
    """
    __tablename__ = "agents"

    # Primary identifier: "kohtravel-travel-assistant"
    id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        doc="Unique agent identifier, typically {app_name}-{agent_type}"
    )

    # Application identifier: "kohtravel"
    app_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Application name that owns this agent"
    )

    # Human-readable name: "Travel Assistant"
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Human-readable agent name"
    )

    # Base system prompt shared across users
    base_system_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Base system prompt for this agent, can be augmented per user"
    )

    # Tool configuration as JSON
    tools_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Tool definitions and configuration as JSON"
    )

    # Model configuration
    model: Mapped[str] = mapped_column(
        String(100),
        default="claude-3-5-sonnet-20241022",
        nullable=False,
        doc="LLM model identifier"
    )

    max_tokens: Mapped[int] = mapped_column(
        Integer,
        default=4096,
        nullable=False,
        doc="Maximum tokens for model responses"
    )

    temperature: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Model temperature setting"
    )

    # Enabled tools list
    enabled_tools: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        doc="List of enabled tool names"
    )

    # Description for documentation/UI
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Optional agent description"
    )

    # Agent status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        doc="Whether this agent is active and available"
    )

    # Relationships
    user_contexts: Mapped[List["UserAgentContextModel"]] = relationship(
        "UserAgentContextModel",
        back_populates="agent",
        cascade="all, delete-orphan",
        doc="User-specific contexts for this agent"
    )

    sessions: Mapped[List["SessionModel"]] = relationship(
        "SessionModel",
        back_populates="agent",
        cascade="all, delete-orphan",
        doc="Conversation sessions for this agent"
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("app_name", "name", name="uq_agent_app_name"),
        Index("ix_agent_app_name", "app_name"),
        Index("ix_agent_name", "name"),
        Index("ix_agent_active", "is_active"),
        Index("ix_agent_app_active", "app_name", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<AgentModel(id={self.id}, app={self.app_name}, name={self.name})>"

    @property
    def full_identifier(self) -> str:
        """Get full agent identifier in format app_name/name"""
        return f"{self.app_name}/{self.name}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary representation"""
        return {
            "id": self.id,
            "app_name": self.app_name,
            "name": self.name,
            "description": self.description,
            "base_system_prompt": self.base_system_prompt,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "enabled_tools": self.enabled_tools,
            "tools_config": self.tools_config,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }