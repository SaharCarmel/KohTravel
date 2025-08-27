"""
Agent chat streaming endpoint as Vercel serverless function
Converted from agent-infrastructure/src/server/routes/agent.py
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
import sys

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from shared.config import get_cors_origins

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import agent infrastructure components
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), '../../../agent-infrastructure/src'))
    from core.agent import Agent, AgentConfig
    from core.streaming import StreamingManager
    from providers.anthropic_provider import AnthropicProvider, AnthropicConfig
    from tools.file_ops import ReadFileTool, WriteFileTool, ListDirectoryTool
    from tools.external import external_registry
    from config.settings import get_settings
except ImportError as e:
    # Fallback for serverless environment
    pass

# User-scoped agent instances
user_agents: Dict[str, Agent] = {}


class ChatMessage(BaseModel):
    session_id: str
    message: str
    project: str = "default"
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


async def get_or_create_agent(project: str, user_id: str, system_prompt: Optional[str] = None) -> Agent:
    """Get or create user-scoped agent for project"""
    from shared.config import get_api_service_url
    
    agent_key = f"{project}:{user_id}"
    
    if system_prompt is not None and agent_key in user_agents:
        del user_agents[agent_key]
    
    if agent_key in user_agents:
        return user_agents[agent_key]
    
    # Create provider
    provider_config = AnthropicConfig(
        api_key=os.getenv('ANTHROPIC_API_KEY'),
        model=os.getenv('DEFAULT_MODEL', 'claude-3-5-sonnet-20241022')
    )
    provider = AnthropicProvider(provider_config)
    
    # Load external tools for project
    project_tools = []
    
    if system_prompt is None:
        system_prompt = "You are a helpful AI assistant."
    
    # Load project-specific tools from main API
    external_tools_config = {
        "kohtravel": f"{get_api_service_url()}/api/agent/tools"
    }
    
    if project in external_tools_config:
        tools_base_url = external_tools_config[project]
        try:
            external_tools = await external_registry.load_tools_from_endpoint(tools_base_url)
            project_tools.extend(external_tools)
        except Exception as e:
            print(f"Failed to load external tools: {e}")
    
    # Create agent config
    agent_config = AgentConfig(
        name=f"{project}-agent-{user_id}",
        system_prompt=system_prompt,
        model=os.getenv('DEFAULT_MODEL', 'claude-3-5-sonnet-20241022'),
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
    
    # Register file operation tools (limited in serverless)
    allowed_paths = ["/tmp"]  # Only /tmp is writable in serverless
    read_tool = ReadFileTool(allowed_paths=allowed_paths)
    agent.register_tool("read_file", read_tool)
    
    user_agents[agent_key] = agent
    return agent


@app.post("/chat/stream")
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
        
        return StreamingResponse(
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
        print(f"Streaming chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export the app for Vercel
def handler(request, context):
    """Vercel serverless function handler"""
    return app