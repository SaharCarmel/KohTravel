"""
Repository pattern implementation for Agent OS database operations

This module provides repository classes that encapsulate database operations
using the repository pattern for clean separation of concerns:

- BaseRepository: Generic CRUD operations
- AgentRepository: Agent-specific database operations
- SessionRepository: Session persistence operations
- UserContextRepository: User context management
"""

from .base import BaseRepository
from .agent_repository import AgentRepository
from .session_repository import SessionRepository
from .user_context_repository import UserContextRepository

__all__ = [
    "BaseRepository",
    "AgentRepository",
    "SessionRepository",
    "UserContextRepository"
]