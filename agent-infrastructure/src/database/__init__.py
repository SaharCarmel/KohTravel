"""
Agent OS Database Module

This module provides database infrastructure for the Agent OS, supporting:
- Agent configuration persistence
- User context management
- Conversation session storage
- Multi-tenant architecture

All database operations are async and use SQLAlchemy 2.0+ patterns.
"""

from .base import Base
from .connection import DatabaseManager, get_async_session, db_manager, ensure_database_initialized

__all__ = [
    "Base",
    "DatabaseManager",
    "get_async_session",
    "db_manager",
    "ensure_database_initialized"
]