"""
Agent Management API Routes

This module implements the complete Agent Management System API following the tech lead's
strategic recommendations. It provides database-driven agent lifecycle management with
comprehensive validation, error handling, and observability.

Key Features:
- Complete CRUD operations for agents
- Tool configuration management with validation
- Health monitoring and status tracking
- Enhanced error handling with structured responses
- Transaction integrity and optimistic locking
- Comprehensive logging with correlation IDs
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid
import asyncio
from contextlib import asynccontextmanager

from fastapi import APIRouter, HTTPException, Depends, Request, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import structlog

from src.database import get_async_session
from src.repositories.agent_repository import AgentRepository
from src.schemas.agent_schemas import (
    AgentCreateRequest,
    AgentUpdateRequest,
    ToolsUpdateRequest,
    AgentResponse,
    AgentListResponse,
    AgentSummary,
    AgentCreatedResponse,
    AgentUpdatedResponse,
    OperationResponse,
    ErrorResponse,
    ValidationError,
    AgentListQuery,
    AgentStatus,
    HealthStatus,
    ToolValidationResult,
    ToolHealthReport,
    UsageMetrics
)
from src.database.models.agent import AgentModel
from src.config.settings import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/agents", tags=["Agent Management"])


def get_correlation_id(request: Request) -> str:
    """Generate or extract correlation ID for request tracing"""
    return request.headers.get("X-Correlation-ID", str(uuid.uuid4()))


@asynccontextmanager
async def transaction_context(session: AsyncSession, correlation_id: str):
    """Enhanced transaction context with comprehensive error handling"""
    try:
        await session.begin()
        logger.info("Transaction started", correlation_id=correlation_id)
        yield session
        await session.commit()
        logger.info("Transaction committed", correlation_id=correlation_id)
    except IntegrityError as e:
        await session.rollback()
        logger.error(
            "Database integrity error",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "INTEGRITY_VIOLATION",
                "message": "Operation violates database constraints",
                "correlation_id": correlation_id
            }
        )
    except Exception as e:
        await session.rollback()
        logger.error(
            "Transaction failed",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "TRANSACTION_FAILED",
                "message": "Database operation failed",
                "correlation_id": correlation_id
            }
        )


def build_agent_id(app_name: str, name: str) -> str:
    """Build standardized agent ID from app name and agent name"""
    # Convert to lowercase and replace spaces/special chars with hyphens
    clean_app = app_name.lower().replace(" ", "-").replace("_", "-")
    clean_name = name.lower().replace(" ", "-").replace("_", "-")
    return f"{clean_app}-{clean_name}"


async def validate_tools_connectivity(
    tools: List[Dict[str, Any]],
    correlation_id: str
) -> List[ToolValidationResult]:
    """Validate tool endpoint connectivity and schemas"""
    results = []

    for tool in tools:
        if tool.get("type") != "external":
            # Skip connectivity check for internal tools
            results.append(ToolValidationResult(
                tool_name=tool["name"],
                is_valid=True,
                connectivity_check=True,
                schema_validation=True,
                last_checked_at=datetime.now(timezone.utc)
            ))
            continue

        # Validate external tool connectivity
        start_time = datetime.now(timezone.utc)
        endpoint_url = tool.get("endpoint_url")

        try:
            # TODO: Implement actual HTTP connectivity check
            # For now, assume valid if URL is provided
            is_connected = bool(endpoint_url)
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            results.append(ToolValidationResult(
                tool_name=tool["name"],
                is_valid=is_connected,
                connectivity_check=is_connected,
                schema_validation=True,  # TODO: Implement schema validation
                response_time_ms=response_time,
                last_checked_at=datetime.now(timezone.utc)
            ))

        except Exception as e:
            logger.warning(
                "Tool connectivity check failed",
                tool_name=tool["name"],
                endpoint_url=endpoint_url,
                error=str(e),
                correlation_id=correlation_id
            )
            results.append(ToolValidationResult(
                tool_name=tool["name"],
                is_valid=False,
                connectivity_check=False,
                schema_validation=False,
                error_message=str(e),
                last_checked_at=datetime.now(timezone.utc)
            ))

    return results


def calculate_agent_metrics(agent: AgentModel) -> UsageMetrics:
    """Calculate usage metrics for an agent"""
    # TODO: Implement actual metrics calculation from sessions
    # For now, return default metrics to avoid lazy loading issues
    return UsageMetrics(
        total_sessions=0,  # TODO: Query sessions separately to avoid lazy loading
        active_sessions=0,  # TODO: Count active sessions
        total_messages=0,   # TODO: Count from conversation history
        total_tool_calls=0, # TODO: Count from conversation history
        last_used_at=None,  # TODO: Get from session data
        avg_response_time_ms=None  # TODO: Calculate from logs
    )


def convert_agent_to_response(agent: AgentModel, include_metrics: bool = True) -> AgentResponse:
    """Convert AgentModel to AgentResponse with enhanced data"""
    # Convert tools_config to tool definitions
    tools = []
    if agent.tools_config:
        for tool_name, tool_config in agent.tools_config.items():
            tools.append({
                "name": tool_name,
                "type": tool_config.get("type", "external"),
                "description": tool_config.get("description", ""),
                "endpoint_url": tool_config.get("endpoint_url"),
                "enabled": tool_name in (agent.enabled_tools or [])
            })

    # Determine health status based on agent state
    health = HealthStatus.HEALTHY if agent.is_active else HealthStatus.UNHEALTHY

    # Calculate usage metrics if requested
    metrics = calculate_agent_metrics(agent) if include_metrics else None

    return AgentResponse(
        id=agent.id,
        app_name=agent.app_name,
        name=agent.name,
        description=agent.description,
        base_system_prompt=agent.base_system_prompt,
        tools=tools,
        model_configuration={
            "model": agent.model,
            "max_tokens": agent.max_tokens,
            "temperature": agent.temperature
        },
        status=AgentStatus.ACTIVE if agent.is_active else AgentStatus.INACTIVE,
        health=health,
        is_active=agent.is_active,
        version=1,  # TODO: Implement version tracking
        usage_metrics=metrics,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    )


# Agent CRUD Operations

@router.post(
    "",
    response_model=AgentCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Agent",
    description="Create a new agent with tools and configuration"
)
async def create_agent(
    agent_data: AgentCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_async_session)
) -> AgentCreatedResponse:
    """
    Create a new agent with comprehensive validation and tool setup.

    This endpoint implements the tech lead's recommendations for:
    - Atomic transaction handling
    - Tool connectivity validation
    - Enhanced error handling
    - Comprehensive logging
    """
    correlation_id = get_correlation_id(request)

    logger.info(
        "Creating new agent",
        app_name=agent_data.app_name,
        name=agent_data.name,
        tools_count=len(agent_data.tools or []),
        correlation_id=correlation_id
    )

    start_time = datetime.now(timezone.utc)

    try:
        async with transaction_context(session, correlation_id):
            repo = AgentRepository(session)

            # Generate agent ID
            agent_id = build_agent_id(agent_data.app_name, agent_data.name)

            # Validate tools if provided
            tool_validation_results = []
            if agent_data.tools:
                tool_validation_results = await validate_tools_connectivity(
                    [tool.dict() for tool in agent_data.tools],
                    correlation_id
                )

                # Check if any tools failed validation
                failed_tools = [r for r in tool_validation_results if not r.is_valid]
                if failed_tools:
                    logger.warning(
                        "Some tools failed validation",
                        agent_id=agent_id,
                        failed_tools=[t.tool_name for t in failed_tools],
                        correlation_id=correlation_id
                    )

            # Prepare tools configuration
            tools_config = {}
            enabled_tools = []

            if agent_data.tools:
                for tool in agent_data.tools:
                    tools_config[tool.name] = {
                        "type": tool.type,
                        "description": tool.description,
                        "endpoint_url": tool.endpoint_url,
                        "input_schema": tool.input_schema.dict() if tool.input_schema else None,
                        "output_schema": tool.output_schema.dict() if tool.output_schema else None,
                        "timeout_seconds": tool.timeout_seconds,
                        "max_retries": tool.max_retries
                    }
                    if tool.enabled:
                        enabled_tools.append(tool.name)

            # Create agent using repository
            agent = await repo.create_agent(
                id=agent_id,
                app_name=agent_data.app_name,
                name=agent_data.name,
                base_system_prompt=agent_data.base_system_prompt,
                model=agent_data.model_configuration.model if agent_data.model_configuration else "claude-3-5-sonnet-20241022",
                max_tokens=agent_data.model_configuration.max_tokens if agent_data.model_configuration else 4096,
                temperature=agent_data.model_configuration.temperature if agent_data.model_configuration else 0.0,
                enabled_tools=enabled_tools,
                tools_config=tools_config,
                description=agent_data.description
            )

            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            logger.info(
                "Agent created successfully",
                agent_id=agent.id,
                app_name=agent.app_name,
                name=agent.name,
                tools_count=len(enabled_tools),
                duration_ms=duration_ms,
                correlation_id=correlation_id
            )

            return AgentCreatedResponse(
                agent_id=agent.id,
                message="Agent created successfully",
                agent=convert_agent_to_response(agent)
            )

    except ValueError as e:
        # Business logic validation errors
        logger.warning(
            "Agent creation validation failed",
            app_name=agent_data.app_name,
            name=agent_data.name,
            error=str(e),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "VALIDATION_FAILED",
                "message": str(e),
                "correlation_id": correlation_id
            }
        )


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get Agent Configuration",
    description="Retrieve complete agent configuration including tools and metrics"
)
async def get_agent(
    agent_id: str,
    request: Request,
    include_metrics: bool = Query(True, description="Include usage metrics in response"),
    session: AsyncSession = Depends(get_async_session)
) -> AgentResponse:
    """Get agent configuration with optional metrics"""
    correlation_id = get_correlation_id(request)

    logger.info(
        "Retrieving agent configuration",
        agent_id=agent_id,
        include_metrics=include_metrics,
        correlation_id=correlation_id
    )

    repo = AgentRepository(session)
    agent = await repo.get_with_relationships(agent_id)

    if not agent:
        logger.warning(
            "Agent not found",
            agent_id=agent_id,
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "AGENT_NOT_FOUND",
                "message": f"Agent '{agent_id}' not found",
                "correlation_id": correlation_id
            }
        )

    return convert_agent_to_response(agent, include_metrics=include_metrics)


@router.get(
    "",
    response_model=AgentListResponse,
    summary="List Agents",
    description="List agents with filtering, pagination, and search capabilities"
)
async def list_agents(
    request: Request,
    query_params: AgentListQuery = Depends(),
    session: AsyncSession = Depends(get_async_session)
) -> AgentListResponse:
    """List agents with comprehensive filtering and pagination"""
    correlation_id = get_correlation_id(request)

    logger.info(
        "Listing agents",
        app_name=query_params.app_name,
        status=query_params.status,
        health=query_params.health,
        search=query_params.search,
        page=query_params.page,
        page_size=query_params.page_size,
        correlation_id=correlation_id
    )

    repo = AgentRepository(session)

    # Calculate offset
    offset = (query_params.page - 1) * query_params.page_size

    # Build filters
    filters = {}
    if query_params.app_name:
        filters["app_name"] = query_params.app_name
    if query_params.status:
        filters["is_active"] = (query_params.status == AgentStatus.ACTIVE)

    # Get agents with filters
    agents = await repo.get_multi(
        offset=offset,
        limit=query_params.page_size,
        order_by=query_params.sort_by,
        **filters
    )

    # TODO: Implement search functionality
    # TODO: Implement total count for pagination
    total = len(agents)  # Placeholder
    total_pages = (total + query_params.page_size - 1) // query_params.page_size

    agent_responses = [convert_agent_to_response(agent, include_metrics=False) for agent in agents]

    return AgentListResponse(
        agents=agent_responses,
        total=total,
        page=query_params.page,
        page_size=query_params.page_size,
        total_pages=total_pages
    )


@router.put(
    "/{agent_id}/prompt",
    response_model=AgentUpdatedResponse,
    summary="Update Agent System Prompt",
    description="Update the base system prompt for an agent"
)
async def update_agent_prompt(
    agent_id: str,
    prompt_update: Dict[str, str],
    request: Request,
    session: AsyncSession = Depends(get_async_session)
) -> AgentUpdatedResponse:
    """Update agent system prompt with validation"""
    correlation_id = get_correlation_id(request)

    new_prompt = prompt_update.get("base_system_prompt")
    if not new_prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "MISSING_PROMPT",
                "message": "base_system_prompt is required",
                "correlation_id": correlation_id
            }
        )

    logger.info(
        "Updating agent system prompt",
        agent_id=agent_id,
        prompt_length=len(new_prompt),
        correlation_id=correlation_id
    )

    try:
        async with transaction_context(session, correlation_id):
            repo = AgentRepository(session)

            updated_agent = await repo.update_system_prompt(agent_id, new_prompt)

            if not updated_agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error_code": "AGENT_NOT_FOUND",
                        "message": f"Agent '{agent_id}' not found",
                        "correlation_id": correlation_id
                    }
                )

            logger.info(
                "Agent system prompt updated",
                agent_id=agent_id,
                correlation_id=correlation_id
            )

            return AgentUpdatedResponse(
                agent_id=agent_id,
                message="System prompt updated successfully",
                version=2,  # TODO: Implement proper versioning
                changes=["base_system_prompt"]
            )

    except Exception as e:
        logger.error(
            "Failed to update agent prompt",
            agent_id=agent_id,
            error=str(e),
            correlation_id=correlation_id
        )
        raise


@router.put(
    "/{agent_id}/tools",
    response_model=AgentUpdatedResponse,
    summary="Update Agent Tools Configuration",
    description="Update the tools configuration for an agent with validation"
)
async def update_agent_tools(
    agent_id: str,
    tools_update: ToolsUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_async_session)
) -> AgentUpdatedResponse:
    """Update agent tools configuration with comprehensive validation"""
    correlation_id = get_correlation_id(request)

    logger.info(
        "Updating agent tools configuration",
        agent_id=agent_id,
        tools_count=len(tools_update.tools),
        correlation_id=correlation_id
    )

    try:
        # Validate tools connectivity
        tool_validation_results = await validate_tools_connectivity(
            [tool.dict() for tool in tools_update.tools],
            correlation_id
        )

        # Check for validation failures
        failed_tools = [r for r in tool_validation_results if not r.is_valid]
        if failed_tools:
            logger.warning(
                "Tool validation failed",
                agent_id=agent_id,
                failed_tools=[t.tool_name for t in failed_tools],
                correlation_id=correlation_id
            )

        async with transaction_context(session, correlation_id):
            repo = AgentRepository(session)

            # Prepare tools configuration
            tools_config = {}
            enabled_tools = []

            for tool in tools_update.tools:
                tools_config[tool.name] = {
                    "type": tool.type,
                    "description": tool.description,
                    "endpoint_url": tool.endpoint_url,
                    "input_schema": tool.input_schema.dict() if tool.input_schema else None,
                    "output_schema": tool.output_schema.dict() if tool.output_schema else None,
                    "timeout_seconds": tool.timeout_seconds,
                    "max_retries": tool.max_retries
                }
                if tool.enabled:
                    enabled_tools.append(tool.name)

            updated_agent = await repo.update_tools_config(
                agent_id,
                tools_config,
                enabled_tools
            )

            if not updated_agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error_code": "AGENT_NOT_FOUND",
                        "message": f"Agent '{agent_id}' not found",
                        "correlation_id": correlation_id
                    }
                )

            logger.info(
                "Agent tools configuration updated",
                agent_id=agent_id,
                tools_count=len(enabled_tools),
                correlation_id=correlation_id
            )

            return AgentUpdatedResponse(
                agent_id=agent_id,
                message="Tools configuration updated successfully",
                version=2,  # TODO: Implement proper versioning
                changes=["tools_config", "enabled_tools"]
            )

    except Exception as e:
        logger.error(
            "Failed to update agent tools",
            agent_id=agent_id,
            error=str(e),
            correlation_id=correlation_id
        )
        raise


@router.delete(
    "/{agent_id}",
    response_model=OperationResponse,
    summary="Deactivate Agent",
    description="Soft delete (deactivate) an agent"
)
async def deactivate_agent(
    agent_id: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session)
) -> OperationResponse:
    """Deactivate an agent (soft delete)"""
    correlation_id = get_correlation_id(request)

    logger.info(
        "Deactivating agent",
        agent_id=agent_id,
        correlation_id=correlation_id
    )

    try:
        async with transaction_context(session, correlation_id):
            repo = AgentRepository(session)

            updated_agent = await repo.set_active_status(agent_id, False)

            if not updated_agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error_code": "AGENT_NOT_FOUND",
                        "message": f"Agent '{agent_id}' not found",
                        "correlation_id": correlation_id
                    }
                )

            logger.info(
                "Agent deactivated successfully",
                agent_id=agent_id,
                correlation_id=correlation_id
            )

            return OperationResponse(
                success=True,
                message="Agent deactivated successfully",
                correlation_id=correlation_id
            )

    except Exception as e:
        logger.error(
            "Failed to deactivate agent",
            agent_id=agent_id,
            error=str(e),
            correlation_id=correlation_id
        )
        raise


# Health and Monitoring Endpoints

@router.get(
    "/{agent_id}/health",
    response_model=ToolHealthReport,
    summary="Check Agent Health",
    description="Comprehensive health check for agent and its tools"
)
async def check_agent_health(
    agent_id: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session)
) -> ToolHealthReport:
    """Perform comprehensive health check for agent and tools"""
    correlation_id = get_correlation_id(request)

    logger.info(
        "Checking agent health",
        agent_id=agent_id,
        correlation_id=correlation_id
    )

    repo = AgentRepository(session)
    agent = await repo.get(agent_id)

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "AGENT_NOT_FOUND",
                "message": f"Agent '{agent_id}' not found",
                "correlation_id": correlation_id
            }
        )

    # Validate tools if agent has any
    tool_results = []
    if agent.tools_config:
        tools_data = []
        for tool_name, tool_config in agent.tools_config.items():
            tools_data.append({
                "name": tool_name,
                "type": tool_config.get("type", "external"),
                "endpoint_url": tool_config.get("endpoint_url")
            })

        tool_results = await validate_tools_connectivity(tools_data, correlation_id)

    healthy_tools = len([r for r in tool_results if r.is_valid])
    total_tools = len(tool_results)

    # Determine overall health
    if total_tools == 0:
        overall_health = HealthStatus.HEALTHY
    elif healthy_tools == total_tools:
        overall_health = HealthStatus.HEALTHY
    elif healthy_tools > 0:
        overall_health = HealthStatus.DEGRADED
    else:
        overall_health = HealthStatus.UNHEALTHY

    return ToolHealthReport(
        agent_id=agent_id,
        total_tools=total_tools,
        healthy_tools=healthy_tools,
        unhealthy_tools=total_tools - healthy_tools,
        tool_results=tool_results,
        overall_health=overall_health,
        last_checked_at=datetime.now(timezone.utc)
    )