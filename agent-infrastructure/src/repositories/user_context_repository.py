"""
User context repository for Agent OS database operations

This module provides user context-specific database operations including:
- User context management per agent
- Preference handling
- Context metadata operations
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import structlog

from .base import BaseRepository
from src.database.models.user_context import UserAgentContextModel

logger = structlog.get_logger(__name__)


class UserContextRepository(BaseRepository[UserAgentContextModel, Dict[str, Any], Dict[str, Any]]):
    """
    Repository for User Agent Context database operations

    Provides specialized methods for user context management including:
    - User context per agent queries
    - Preference management
    - Context metadata operations
    - User session context relationships
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    @property
    def model(self) -> type[UserAgentContextModel]:
        return UserAgentContextModel

    async def get_by_agent_and_user(
        self,
        agent_id: str,
        user_id: str
    ) -> Optional[UserAgentContextModel]:
        """
        Get user context by agent and user ID

        Args:
            agent_id: Agent identifier
            user_id: User identifier

        Returns:
            User context model or None if not found
        """
        try:
            result = await self.session.execute(
                select(UserAgentContextModel)
                .where(
                    and_(
                        UserAgentContextModel.agent_id == agent_id,
                        UserAgentContextModel.user_id == user_id
                    )
                )
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "Failed to get user context by agent and user",
                agent_id=agent_id,
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_by_user(
        self,
        user_id: str,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 100
    ) -> List[UserAgentContextModel]:
        """
        Get all user contexts for a specific user

        Args:
            user_id: User identifier
            active_only: Whether to return only active contexts
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of user contexts for the user
        """
        filters = {"user_id": user_id}
        if active_only:
            filters["is_active"] = True

        return await self.get_multi(
            offset=offset,
            limit=limit,
            order_by="agent_id",
            **filters
        )

    async def get_by_agent(
        self,
        agent_id: str,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 100
    ) -> List[UserAgentContextModel]:
        """
        Get all user contexts for a specific agent

        Args:
            agent_id: Agent identifier
            active_only: Whether to return only active contexts
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of user contexts for the agent
        """
        filters = {"agent_id": agent_id}
        if active_only:
            filters["is_active"] = True

        return await self.get_multi(
            offset=offset,
            limit=limit,
            order_by="user_id",
            **filters
        )

    async def create_user_context(
        self,
        agent_id: str,
        user_id: str,
        custom_prompt_addons: Optional[str] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        context_metadata: Optional[Dict[str, Any]] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> UserAgentContextModel:
        """
        Create a new user context

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            custom_prompt_addons: Custom prompt additions
            user_preferences: User preferences dictionary
            context_metadata: Context metadata dictionary
            settings: User-specific settings

        Returns:
            Created user context model

        Raises:
            ValueError: If user context already exists for this agent/user pair
        """
        try:
            # Check if context already exists
            existing = await self.get_by_agent_and_user(agent_id, user_id)
            if existing:
                raise ValueError(f"User context already exists for agent '{agent_id}' and user '{user_id}'")

            context_data = {
                "agent_id": agent_id,
                "user_id": user_id,
                "custom_prompt_addons": custom_prompt_addons,
                "user_preferences": user_preferences or {},
                "context_metadata": context_metadata or {},
                "settings": settings or {},
                "is_active": True
            }

            return await self.create(context_data)

        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "Failed to create user context",
                agent_id=agent_id,
                user_id=user_id,
                error=str(e)
            )
            raise

    async def update_preferences(
        self,
        agent_id: str,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> Optional[UserAgentContextModel]:
        """
        Update user preferences for an agent

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            preferences: New user preferences

        Returns:
            Updated user context or None if not found
        """
        try:
            context = await self.get_by_agent_and_user(agent_id, user_id)
            if not context:
                return None

            return await self.update(context.id, {"user_preferences": preferences})

        except Exception as e:
            logger.error(
                "Failed to update user preferences",
                agent_id=agent_id,
                user_id=user_id,
                error=str(e)
            )
            raise

    async def update_prompt_addons(
        self,
        agent_id: str,
        user_id: str,
        prompt_addons: str
    ) -> Optional[UserAgentContextModel]:
        """
        Update custom prompt additions for a user

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            prompt_addons: Custom prompt additions

        Returns:
            Updated user context or None if not found
        """
        try:
            context = await self.get_by_agent_and_user(agent_id, user_id)
            if not context:
                return None

            return await self.update(context.id, {"custom_prompt_addons": prompt_addons})

        except Exception as e:
            logger.error(
                "Failed to update prompt addons",
                agent_id=agent_id,
                user_id=user_id,
                error=str(e)
            )
            raise

    async def update_context_metadata(
        self,
        agent_id: str,
        user_id: str,
        metadata: Dict[str, Any]
    ) -> Optional[UserAgentContextModel]:
        """
        Update context metadata for a user

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            metadata: Context metadata

        Returns:
            Updated user context or None if not found
        """
        try:
            context = await self.get_by_agent_and_user(agent_id, user_id)
            if not context:
                return None

            return await self.update(context.id, {"context_metadata": metadata})

        except Exception as e:
            logger.error(
                "Failed to update context metadata",
                agent_id=agent_id,
                user_id=user_id,
                error=str(e)
            )
            raise

    async def set_active_status(
        self,
        agent_id: str,
        user_id: str,
        is_active: bool
    ) -> Optional[UserAgentContextModel]:
        """
        Set user context active status

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            is_active: Whether context should be active

        Returns:
            Updated user context or None if not found
        """
        try:
            context = await self.get_by_agent_and_user(agent_id, user_id)
            if not context:
                return None

            return await self.update(context.id, {"is_active": is_active})

        except Exception as e:
            logger.error(
                "Failed to set context active status",
                agent_id=agent_id,
                user_id=user_id,
                is_active=is_active,
                error=str(e)
            )
            raise

    async def get_with_relationships(
        self,
        agent_id: str,
        user_id: str
    ) -> Optional[UserAgentContextModel]:
        """
        Get user context with all relationships loaded

        Args:
            agent_id: Agent identifier
            user_id: User identifier

        Returns:
            User context with relationships or None if not found
        """
        try:
            result = await self.session.execute(
                select(UserAgentContextModel)
                .options(
                    selectinload(UserAgentContextModel.agent),
                    selectinload(UserAgentContextModel.sessions)
                )
                .where(
                    and_(
                        UserAgentContextModel.agent_id == agent_id,
                        UserAgentContextModel.user_id == user_id
                    )
                )
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "Failed to get user context with relationships",
                agent_id=agent_id,
                user_id=user_id,
                error=str(e)
            )
            raise

    def _add_relationship_loading(self, query):
        """Add relationship loading for user contexts"""
        return query.options(
            selectinload(UserAgentContextModel.agent),
            selectinload(UserAgentContextModel.sessions)
        )