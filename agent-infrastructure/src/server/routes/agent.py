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
from src.providers.anthropic_provider import AnthropicProvider, AnthropicConfig
from src.tools.file_ops import ReadFileTool, WriteFileTool, ListDirectoryTool
from src.tools.external import external_registry
from src.config.settings import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter()

# Global agent instances (in production, use proper DI/registry)
agents: Dict[str, Agent] = {}


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


async def get_or_create_agent(project: str) -> Agent:
    """Get or create agent for project"""
    if project in agents:
        return agents[project]
    
    settings = get_settings()
    
    # Create provider
    provider_config = AnthropicConfig(
        api_key=settings.anthropic_api_key,
        model=settings.default_model
    )
    provider = AnthropicProvider(provider_config)
    
    # Load external tools and system prompt for project
    system_prompt = "You are a helpful AI assistant."
    project_tools = []
    
    # Try to load project-specific configuration
    if project == "kohtravel":
        # Load KohTravel tools from backend API
        kohtravel_base_url = "http://localhost:8000/api/agent/tools"
        try:
            external_tools = await external_registry.load_tools_from_endpoint(kohtravel_base_url)
            project_tools.extend(external_tools)
            
            # Load system prompt
            external_prompt = await external_registry.load_system_prompt(kohtravel_base_url)
            if external_prompt:
                system_prompt = external_prompt
                
        except Exception as e:
            logger.warning("Failed to load external tools", project=project, error=str(e))
    
    # Create agent config
    agent_config = AgentConfig(
        name=f"{project}-agent",
        system_prompt=system_prompt,
        model=settings.default_model,
        enabled_tools=[tool.name for tool in project_tools] + ["read_file"]
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
    
    agents[project] = agent
    logger.info("Agent created", project=project, tools=list(agent.tools.keys()))
    
    return agent


@router.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage, request: Request):
    """Send a message to the agent"""
    try:
        agent = await get_or_create_agent(message.project)
        
        # Build context
        context = message.context or {}
        if message.user_id:
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
        agent = await get_or_create_agent(message.project)
        
        # Build context
        context = message.context or {}
        if message.user_id:
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
async def get_conversation(session_id: str, project: str = "default"):
    """Get conversation history"""
    try:
        agent = await get_or_create_agent(project)
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
async def clear_conversation(session_id: str, project: str = "default"):
    """Clear conversation history"""
    try:
        agent = await get_or_create_agent(project)
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
    """List all active agents"""
    agent_info = []
    
    for project, agent in agents.items():
        agent_info.append({
            "project": project,
            "name": agent.config.name,
            "model": agent.config.model,
            "tools": list(agent.tools.keys()),
            "conversations": len(agent.conversations)
        })
    
    return {"agents": agent_info}


@router.get("/tools")
async def list_tools(project: str = "default"):
    """List available tools for a project"""
    try:
        agent = await get_or_create_agent(project)
        
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