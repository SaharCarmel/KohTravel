"""
Agent interaction routes
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse as FastAPIStreamingResponse
from pydantic import BaseModel
import structlog

from src.core.agent import Agent, AgentConfig
from src.core.streaming import StreamingManager
from src.core.tool_registry import tool_registry
from src.providers.anthropic_provider import AnthropicProvider, AnthropicConfig
from src.tools.file_ops import ReadFileTool, WriteFileTool, ListDirectoryTool
from src.tools.external import external_registry, ExternalTool
from src.schemas.tool_schemas import ToolDefinition, ToolType, ToolHealthStatus
from src.config.settings import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter()

# User-scoped agent instances for multi-user support
# Key format: "{project}:{user_id}"
user_agents: Dict[str, Agent] = {}


async def _create_external_tool_from_definition(tool_def: ToolDefinition) -> Optional[ExternalTool]:
    """
    Convert a ToolDefinition to an ExternalTool object for agent registration.

    This helper function bridges the new dynamic tool system with the existing
    ExternalTool implementation for backward compatibility.
    """
    try:
        # Build parameters schema from tool definition
        parameters_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        if tool_def.input_schema and tool_def.input_schema.properties:
            for param_name, param_def in tool_def.input_schema.properties.items():
                parameters_schema["properties"][param_name] = {
                    "type": param_def.type,
                    "description": param_def.description
                }

                if param_def.required:
                    parameters_schema["required"].append(param_name)

                if param_def.default is not None:
                    parameters_schema["properties"][param_name]["default"] = param_def.default

                if param_def.enum:
                    parameters_schema["properties"][param_name]["enum"] = param_def.enum

        # Create ExternalTool instance
        external_tool = ExternalTool(
            name=tool_def.name,
            description=tool_def.description,
            endpoint_url=tool_def.endpoint_url,
            parameters_schema=parameters_schema,
            timeout=tool_def.security_policy.timeout_seconds if tool_def.security_policy else 30
        )

        logger.debug(
            "Created ExternalTool from ToolDefinition",
            tool_name=tool_def.name,
            endpoint_url=tool_def.endpoint_url,
            param_count=len(parameters_schema.get("properties", {}))
        )

        return external_tool

    except Exception as e:
        logger.error(
            "Failed to create ExternalTool from ToolDefinition",
            tool_name=tool_def.name,
            error=str(e)
        )
        return None


class ChatMessage(BaseModel):
    session_id: str
    message: str
    project: str = "default"
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    session_id: str
    status: str
    message: str


async def get_or_create_agent(project: str, user_id: str, system_prompt: Optional[str] = None) -> Agent:
    """
    Get or create user-scoped agent for project using database-driven configuration.

    This function replaces the hardcoded agent creation logic with database-driven
    agent management as recommended by the tech lead.
    """
    from src.database import get_async_session, db_manager
    from src.repositories.agent_repository import AgentRepository

    agent_key = f"{project}:{user_id}"

    # If system_prompt is provided, always create fresh agent (for prompt updates)
    if system_prompt is not None and agent_key in user_agents:
        logger.info("Recreating agent with new system prompt", project=project, user_id=user_id)
        del user_agents[agent_key]  # Clear cached agent

    if agent_key in user_agents:
        return user_agents[agent_key]

    settings = get_settings()

    # Try to load agent from database if Agent OS is enabled
    agent_model = None
    if settings.agent_os_enabled:
        try:
            async with db_manager.get_session() as session:
                repo = AgentRepository(session)

                # Look for agent by app name (project)
                agents = await repo.get_by_app(project, active_only=True)

                if agents:
                    # Use the first active agent for this app
                    agent_model = agents[0]
                    logger.info(
                        "Found agent in database",
                        project=project,
                        agent_id=agent_model.id,
                        tools_count=len(agent_model.enabled_tools or [])
                    )
                else:
                    logger.warning(
                        "No active agent found for project",
                        project=project,
                        user_id=user_id
                    )
        except Exception as e:
            logger.warning(
                "Failed to load agent from database, falling back to legacy mode",
                project=project,
                error=str(e)
            )

    # Create provider
    provider_config = AnthropicConfig(
        api_key=settings.anthropic_api_key,
        model=agent_model.model if agent_model else settings.default_model
    )
    provider = AnthropicProvider(provider_config)

    # Determine system prompt: use provided, then database, then default
    final_system_prompt = system_prompt
    if final_system_prompt is None and agent_model:
        final_system_prompt = agent_model.base_system_prompt
    if final_system_prompt is None:
        final_system_prompt = "You are a helpful AI assistant."

    # Enhanced tool loading with dynamic registry and health validation
    project_tools = []
    validated_tools = []

    # Initialize tool registry with database session
    try:
        if settings.agent_os_enabled:
            async with db_manager.get_session() as session:
                await tool_registry.initialize(session)
    except Exception as e:
        logger.warning("Failed to initialize tool registry with database", error=str(e))

    # Load tools using dynamic tool registry (hybrid approach)
    if agent_model:
        try:
            # Load tools from dynamic registry for this agent
            tool_definitions = await tool_registry.get_agent_tools(agent_model.id)

            if tool_definitions:
                # Convert ToolDefinitions to ExternalTool objects and validate health
                for tool_def in tool_definitions:
                    # Validate tool health before including
                    if await tool_registry.validate_tool_health(tool_def):
                        if tool_def.type == ToolType.EXTERNAL and tool_def.endpoint_url:
                            # Create ExternalTool from ToolDefinition
                            external_tool = await _create_external_tool_from_definition(tool_def)
                            if external_tool:
                                project_tools.append(external_tool)
                                validated_tools.append(tool_def.name)
                        elif tool_def.type in [ToolType.INTERNAL, ToolType.BUILTIN]:
                            # Handle internal tools (placeholder for future implementation)
                            pass
                            validated_tools.append(tool_def.name)
                    else:
                        logger.warning(
                            "Tool failed health validation, skipping",
                            tool_name=tool_def.name,
                            health_status=await tool_registry.get_tool_health_status(tool_def.name)
                        )


            else:
                pass  # No dynamic tools found

        except Exception as e:
            logger.warning(
                "Failed to load tools from dynamic registry, falling back to legacy",
                project=project,
                error=str(e)
            )

    # Fallback to legacy configuration if no dynamic tools or if agent_model is None
    if not project_tools:
        logger.info(
            "Using legacy tool configuration",
            project=project,
            reason="agent_os_disabled" if not settings.agent_os_enabled else "no_dynamic_tools_found"
        )

        # Legacy hardcoded configuration (will be removed in Phase 2.5)
        import os
        api_url = os.getenv('MAIN_API_URL', 'http://localhost:8000')

        external_tools_config = {
            "kohtravel": f"{api_url}/api/agent/tools"
            # Add other projects here as needed
        }

        if project in external_tools_config:
            tools_base_url = external_tools_config[project]
            try:
                external_tools = await external_registry.load_tools_from_endpoint(tools_base_url)
                project_tools.extend(external_tools)
            except Exception as e:
                logger.warning("Failed to load external tools (legacy)", project=project, error=str(e))

    # Create agent config
    agent_config = AgentConfig(
        name=f"{project}-agent-{user_id}",
        system_prompt=final_system_prompt,
        model=agent_model.model if agent_model else settings.default_model,
        enabled_tools=[tool.name for tool in project_tools] + ["read_file"],
        max_tokens=agent_model.max_tokens if agent_model else 4096,
        temperature=agent_model.temperature if agent_model else 0.0
    )

    # Create agent
    agent = Agent(
        config=agent_config,
        provider=provider,
        tools={}
    )

    # Register external tools
    for tool in project_tools:
        agent.register_tool(tool.name, tool)

    # Register standard file operation tools
    read_tool = ReadFileTool(allowed_paths=settings.allowed_file_paths)
    agent.register_tool("read_file", read_tool)

    if settings.allow_file_write:
        write_tool = WriteFileTool(allowed_paths=settings.allowed_file_paths)
        agent.register_tool("write_file", write_tool)

        list_tool = ListDirectoryTool(allowed_paths=settings.allowed_file_paths)
        agent.register_tool("list_directory", list_tool)

    user_agents[agent_key] = agent

    logger.info(
        "User agent created",
        project=project,
        user_id=user_id,
        tool_count=len(agent.tools),
        agent_id=agent_model.id if agent_model else "legacy"
    )

    return agent


@router.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage, request: Request):
    """Send a message to the agent"""
    try:
        if not message.user_id:
            raise HTTPException(status_code=400, detail="User ID is required for multi-user support")
            
        agent = await get_or_create_agent(message.project, message.user_id)
        
        # Build context
        context = message.context or {}
        context["user_id"] = message.user_id
        
        # Send message (collect full response for non-streaming)
        response_generator = agent.send_message(
            session_id=message.session_id,
            message=message.message,
            context=context
        )
        
        # Collect full response
        full_response = await StreamingManager.collect_full_response(response_generator)
        
        return ChatResponse(
            session_id=message.session_id,
            status="success" if full_response["success"] else "error",
            message=full_response["content"]
        )
        
    except Exception as e:
        logger.error("Chat error", error=str(e), session=message.session_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(message: ChatMessage, request: Request):
    """Stream a conversation with the agent"""
    try:
        if not message.user_id:
            raise HTTPException(status_code=400, detail="User ID is required for multi-user support")
            
        agent = await get_or_create_agent(message.project, message.user_id)
        
        # Build context
        context = message.context or {}
        context["user_id"] = message.user_id
        
        # Send message and get streaming response
        response_generator = agent.send_message(
            session_id=message.session_id,
            message=message.message,
            context=context
        )
        
        # Convert to SSE stream
        sse_stream = StreamingManager.to_sse_stream(response_generator)
        
        return FastAPIStreamingResponse(
            sse_stream,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        logger.error("Streaming chat error", error=str(e), session=message.session_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/{session_id}")
async def get_conversation(session_id: str, project: str = "default", user_id: str = None):
    """Get conversation history"""
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
            
        agent = await get_or_create_agent(project, user_id)
        history = agent.get_conversation_history(session_id)
        
        return {
            "session_id": session_id,
            "project": project,
            "messages": history
        }
        
    except Exception as e:
        logger.error("Get conversation error", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversation/{session_id}")
async def clear_conversation(session_id: str, project: str = "default", user_id: str = None):
    """Clear conversation history"""
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
            
        agent = await get_or_create_agent(project, user_id)
        agent.clear_conversation(session_id)
        
        return {
            "session_id": session_id,
            "project": project,
            "status": "cleared"
        }
        
    except Exception as e:
        logger.error("Clear conversation error", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def list_agents():
    """List all active user agents"""
    agent_info = []
    
    for agent_key, agent in user_agents.items():
        project, user_id = agent_key.split(":", 1)
        agent_info.append({
            "agent_key": agent_key,
            "project": project,
            "user_id": user_id,
            "name": agent.config.name,
            "model": agent.config.model,
            "tools": list(agent.tools.keys()),
            "conversations": len(agent.conversations)
        })
    
    return {"agents": agent_info}


@router.get("/tools")
async def list_tools(project: str = "default", user_id: str = None):
    """List available tools for a project"""
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
            
        agent = await get_or_create_agent(project, user_id)
        
        tools_info = []
        for name, tool in agent.tools.items():
            tools_info.append(tool.to_dict())
        
        return {
            "project": project,
            "tools": tools_info
        }
        
    except Exception as e:
        logger.error("List tools error", error=str(e), project=project)
        raise HTTPException(status_code=500, detail=str(e))