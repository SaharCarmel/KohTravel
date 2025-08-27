"""
Agent initialization routes - for setting up agents with custom configuration
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import structlog

from .agent import get_or_create_agent

logger = structlog.get_logger(__name__)

router = APIRouter()


class AgentInitRequest(BaseModel):
    project: str
    system_prompt: str
    session_id: str
    user_id: str


class AgentInitResponse(BaseModel):
    status: str
    project: str
    session_id: str
    message: str


@router.post("/init", response_model=AgentInitResponse)
async def initialize_agent(request: AgentInitRequest):
    """Initialize an agent with custom system prompt"""
    try:
        # Create agent with injected system prompt
        if not request.user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
            
        # Log prompt details for verification
        logger.info("Initializing agent with custom prompt", 
                   project=request.project,
                   user_id=request.user_id,
                   session_id=request.session_id,
                   prompt_length=len(request.system_prompt),
                   contains_workflow=("tool_workflow" in request.system_prompt),
                   prompt_sample=request.system_prompt[:200] + "..." if len(request.system_prompt) > 200 else request.system_prompt)
        
        agent = await get_or_create_agent(
            project=request.project,
            user_id=request.user_id, 
            system_prompt=request.system_prompt
        )
        
        logger.info("Agent initialized successfully with custom prompt", 
                   project=request.project, 
                   session_id=request.session_id)
        
        return AgentInitResponse(
            status="success",
            project=request.project,
            session_id=request.session_id,
            message=f"Agent initialized for {request.project}"
        )
        
    except Exception as e:
        logger.error("Agent initialization error", 
                    project=request.project, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))