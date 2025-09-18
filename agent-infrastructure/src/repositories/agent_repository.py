"""
Agent repository for Agent OS database operations

This module provides agent-specific database operations including:
- Agent configuration management
- Multi-tenant agent queries
- Tool configuration handling
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import structlog

from .base import BaseRepository
from src.database.models.agent import AgentModel

logger = structlog.get_logger(__name__)


class AgentRepository(BaseRepository[AgentModel, Dict[str, Any], Dict[str, Any]]):
    """
    Repository for Agent database operations

    Provides specialized methods for agent management including:
    - Multi-tenant agent queries by app_name
    - Tool configuration validation
    - Agent status management
    - Relationship loading for user contexts and sessions
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    @property
    def model(self) -> type[AgentModel]:
        return AgentModel

    async def get_by_app_and_name(self, app_name: str, name: str) -> Optional[AgentModel]:
        """
        Get agent by application name and agent name

        Args:
            app_name: Application identifier
            name: Agent name

        Returns:
            Agent model or None if not found
        """
        try:
            result = await self.session.execute(
                select(AgentModel)
                .where(AgentModel.app_name == app_name)
                .where(AgentModel.name == name)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "Failed to get agent by app and name",
                app_name=app_name,
                name=name,
                error=str(e)
            )
            raise

    async def get_by_app(
        self,
        app_name: str,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 100
    ) -> List[AgentModel]:
        """
        Get agents by application name

        Args:
            app_name: Application identifier
            active_only: Whether to return only active agents
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of agents for the application
        """
        try:
            query = select(AgentModel).where(AgentModel.app_name == app_name)

            if active_only:
                query = query.where(AgentModel.is_active == True)

            query = query.offset(offset).limit(limit).order_by(AgentModel.name)

            result = await self.session.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(
                "Failed to get agents by app",
                app_name=app_name,
                active_only=active_only,
                error=str(e)
            )
            raise

    async def get_active_agents(
        self,
        offset: int = 0,
        limit: int = 100
    ) -> List[AgentModel]:
        """
        Get all active agents across applications

        Args:
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of active agents
        """
        return await self.get_multi(
            offset=offset,
            limit=limit,
            order_by="app_name",
            is_active=True
        )

    async def create_agent(
        self,
        id: str,
        app_name: str,
        name: str,
        base_system_prompt: str,
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 4096,
        temperature: float = 0.0,
        enabled_tools: Optional[List[str]] = None,
        tools_config: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ) -> AgentModel:
        """
        Create a new agent with validation

        Args:
            id: Unique agent identifier
            app_name: Application identifier
            name: Human-readable agent name
            base_system_prompt: Base system prompt
            model: LLM model identifier
            max_tokens: Maximum tokens for responses
            temperature: Model temperature
            enabled_tools: List of enabled tool names
            tools_config: Tool configuration dictionary
            description: Optional agent description

        Returns:
            Created agent model

        Raises:
            ValueError: If agent with same app_name and name already exists
        """
        try:
            # Check if agent already exists
            existing = await self.get_by_app_and_name(app_name, name)
            if existing:
                raise ValueError(f"Agent '{name}' already exists for app '{app_name}'")

            agent_data = {
                "id": id,
                "app_name": app_name,
                "name": name,
                "base_system_prompt": base_system_prompt,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "enabled_tools": enabled_tools or [],
                "tools_config": tools_config or {},
                "description": description,
                "is_active": True
            }

            return await self.create(agent_data)

        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "Failed to create agent",
                id=id,
                app_name=app_name,
                name=name,
                error=str(e)
            )
            raise

    async def update_system_prompt(self, agent_id: str, system_prompt: str) -> Optional[AgentModel]:
        """
        Update agent's base system prompt

        Args:
            agent_id: Agent identifier
            system_prompt: New system prompt

        Returns:
            Updated agent or None if not found
        """
        return await self.update(agent_id, {"base_system_prompt": system_prompt})

    async def update_tools_config(
        self,
        agent_id: str,
        tools_config: Dict[str, Any],
        enabled_tools: Optional[List[str]] = None
    ) -> Optional[AgentModel]:
        """
        Update agent's tools configuration

        Args:
            agent_id: Agent identifier
            tools_config: New tools configuration
            enabled_tools: Optional list of enabled tools

        Returns:
            Updated agent or None if not found
        """
        update_data = {"tools_config": tools_config}
        if enabled_tools is not None:
            update_data["enabled_tools"] = enabled_tools

        return await self.update(agent_id, update_data)

    async def set_active_status(self, agent_id: str, is_active: bool) -> Optional[AgentModel]:
        """
        Set agent active status

        Args:
            agent_id: Agent identifier
            is_active: Whether agent should be active

        Returns:
            Updated agent or None if not found
        """
        return await self.update(agent_id, {"is_active": is_active})

    async def get_with_relationships(self, agent_id: str) -> Optional[AgentModel]:
        """
        Get agent with all relationships loaded

        Args:
            agent_id: Agent identifier

        Returns:
            Agent with relationships or None if not found
        """
        try:
            result = await self.session.execute(
                select(AgentModel)
                .options(
                    selectinload(AgentModel.user_contexts),
                    selectinload(AgentModel.sessions)
                )
                .where(AgentModel.id == agent_id)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "Failed to get agent with relationships",
                agent_id=agent_id,
                error=str(e)
            )
            raise

    def _add_relationship_loading(self, query):
        """Add relationship loading for agents"""
        return query.options(
            selectinload(AgentModel.user_contexts),
            selectinload(AgentModel.sessions)
        )