"""
Session repository for Agent OS database operations

This module provides session-specific database operations including:
- Conversation session management
- Message history persistence
- Session cleanup and archival
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
import structlog
import uuid

from .base import BaseRepository
from src.database.models.session import SessionModel

logger = structlog.get_logger(__name__)


class SessionRepository(BaseRepository[SessionModel, Dict[str, Any], Dict[str, Any]]):
    """
    Repository for Session database operations

    Provides specialized methods for session management including:
    - Conversation session lifecycle
    - Message history operations
    - Session cleanup and archival
    - User and agent session queries
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    @property
    def model(self) -> type[SessionModel]:
        return SessionModel

    async def get_by_agent_and_user(
        self,
        agent_id: str,
        user_id: str,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 50
    ) -> List[SessionModel]:
        """
        Get sessions by agent and user

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            active_only: Whether to return only active sessions
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of sessions for the agent/user pair
        """
        filters = {
            "agent_id": agent_id,
            "user_id": user_id
        }
        if active_only:
            filters["is_active"] = True

        return await self.get_multi(
            offset=offset,
            limit=limit,
            order_by="-last_active_at",
            **filters
        )

    async def get_by_user(
        self,
        user_id: str,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 50
    ) -> List[SessionModel]:
        """
        Get all sessions for a user across all agents

        Args:
            user_id: User identifier
            active_only: Whether to return only active sessions
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of sessions for the user
        """
        filters = {"user_id": user_id}
        if active_only:
            filters["is_active"] = True

        return await self.get_multi(
            offset=offset,
            limit=limit,
            order_by="-last_active_at",
            **filters
        )

    async def get_by_agent(
        self,
        agent_id: str,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 50
    ) -> List[SessionModel]:
        """
        Get all sessions for an agent across all users

        Args:
            agent_id: Agent identifier
            active_only: Whether to return only active sessions
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of sessions for the agent
        """
        filters = {"agent_id": agent_id}
        if active_only:
            filters["is_active"] = True

        return await self.get_multi(
            offset=offset,
            limit=limit,
            order_by="-last_active_at",
            **filters
        )

    async def create_session(
        self,
        agent_id: str,
        user_id: str,
        user_context_id: Optional[int] = None,
        title: Optional[str] = None,
        session_metadata: Optional[Dict[str, Any]] = None
    ) -> SessionModel:
        """
        Create a new conversation session

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            user_context_id: Optional user context reference
            title: Optional session title
            session_metadata: Optional session metadata

        Returns:
            Created session model
        """
        try:
            session_data = {
                "id": str(uuid.uuid4()),
                "agent_id": agent_id,
                "user_id": user_id,
                "user_context_id": user_context_id,
                "title": title,
                "session_metadata": session_metadata or {},
                "conversation_history": [],
                "message_count": 0,
                "is_active": True,
                "last_active_at": datetime.now(timezone.utc)
            }

            session = await self.create(session_data)

            logger.info(
                "Session created successfully",
                session_id=session.id,
                agent_id=agent_id,
                user_id=user_id
            )

            return session

        except Exception as e:
            logger.error(
                "Failed to create session",
                agent_id=agent_id,
                user_id=user_id,
                error=str(e)
            )
            raise

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[SessionModel]:
        """
        Add a message to session conversation history

        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system, tool)
            content: Message content
            metadata: Optional message metadata

        Returns:
            Updated session or None if not found
        """
        try:
            session = await self.get(session_id)
            if not session:
                logger.warning("Session not found for adding message", session_id=session_id)
                return None

            # Add message to conversation history
            session.add_message(role, content, metadata)

            # Update the session in database
            await self.session.commit()
            await self.session.refresh(session)

            logger.debug(
                "Message added to session",
                session_id=session_id,
                role=role,
                message_count=session.message_count
            )

            return session

        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to add message to session",
                session_id=session_id,
                role=role,
                error=str(e)
            )
            raise

    async def update_activity(self, session_id: str) -> Optional[SessionModel]:
        """
        Update session last activity timestamp

        Args:
            session_id: Session identifier

        Returns:
            Updated session or None if not found
        """
        return await self.update(
            session_id,
            {"last_active_at": datetime.now(timezone.utc)}
        )

    async def set_title(self, session_id: str, title: str) -> Optional[SessionModel]:
        """
        Set session title

        Args:
            session_id: Session identifier
            title: New session title

        Returns:
            Updated session or None if not found
        """
        return await self.update(session_id, {"title": title})

    async def set_active_status(self, session_id: str, is_active: bool) -> Optional[SessionModel]:
        """
        Set session active status

        Args:
            session_id: Session identifier
            is_active: Whether session should be active

        Returns:
            Updated session or None if not found
        """
        return await self.update(session_id, {"is_active": is_active})

    async def clear_conversation_history(self, session_id: str) -> Optional[SessionModel]:
        """
        Clear conversation history for a session

        Args:
            session_id: Session identifier

        Returns:
            Updated session or None if not found
        """
        try:
            session = await self.get(session_id)
            if not session:
                return None

            session.clear_history()

            await self.session.commit()
            await self.session.refresh(session)

            logger.info("Session conversation history cleared", session_id=session_id)
            return session

        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to clear session history",
                session_id=session_id,
                error=str(e)
            )
            raise

    async def get_inactive_sessions(
        self,
        inactive_since: datetime,
        limit: int = 100
    ) -> List[SessionModel]:
        """
        Get sessions that have been inactive since a specific time

        Args:
            inactive_since: DateTime threshold for inactive sessions
            limit: Maximum number of sessions to return

        Returns:
            List of inactive sessions
        """
        try:
            result = await self.session.execute(
                select(SessionModel)
                .where(SessionModel.last_active_at < inactive_since)
                .where(SessionModel.is_active == True)
                .order_by(SessionModel.last_active_at)
                .limit(limit)
            )
            return list(result.scalars().all())

        except Exception as e:
            logger.error(
                "Failed to get inactive sessions",
                inactive_since=inactive_since,
                error=str(e)
            )
            raise

    async def cleanup_old_sessions(
        self,
        older_than_days: int = 30,
        batch_size: int = 100,
        archive: bool = True
    ) -> int:
        """
        Cleanup old inactive sessions

        Args:
            older_than_days: Number of days to consider sessions old
            batch_size: Number of sessions to process in each batch
            archive: Whether to archive (set inactive) or delete sessions

        Returns:
            Number of sessions processed
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)

            inactive_sessions = await self.get_inactive_sessions(
                inactive_since=cutoff_date,
                limit=batch_size
            )

            count = 0
            for session in inactive_sessions:
                if archive:
                    await self.set_active_status(session.id, False)
                else:
                    await self.delete(session.id)
                count += 1

            logger.info(
                "Session cleanup completed",
                processed_count=count,
                older_than_days=older_than_days,
                archived=archive
            )

            return count

        except Exception as e:
            logger.error(
                "Failed to cleanup old sessions",
                older_than_days=older_than_days,
                error=str(e)
            )
            raise

    async def get_with_relationships(self, session_id: str) -> Optional[SessionModel]:
        """
        Get session with all relationships loaded

        Args:
            session_id: Session identifier

        Returns:
            Session with relationships or None if not found
        """
        try:
            result = await self.session.execute(
                select(SessionModel)
                .options(
                    selectinload(SessionModel.agent),
                    selectinload(SessionModel.user_context)
                )
                .where(SessionModel.id == session_id)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "Failed to get session with relationships",
                session_id=session_id,
                error=str(e)
            )
            raise

    def _add_relationship_loading(self, query):
        """Add relationship loading for sessions"""
        return query.options(
            selectinload(SessionModel.agent),
            selectinload(SessionModel.user_context)
        )