"""
Agent chat endpoint that includes KohTravel-specific context
"""
import httpx
import os
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional
import structlog

from database import get_db
from services.auth import get_current_user
from services.context_service import TravelContextService
from models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(
    tags=["chat"]
)


class ChatRequest(BaseModel):
    session_id: str
    message: str
    context: Optional[Dict[str, Any]] = None


@router.post("/chat/stream")
async def chat_with_context(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Chat with agent including KohTravel-specific context
    Routes to agent infrastructure with enhanced context
    """
    try:
        # Generate travel-specific context
        travel_context = await TravelContextService.get_agent_context(
            current_user.email, db
        )
        
        # Merge with any existing context from frontend
        enhanced_context = {
            **(request.context or {}),
            **travel_context,
            "user_name": current_user.name,
            "user_email": current_user.email
        }
        
        # Prepare request for agent infrastructure
        agent_request = {
            "session_id": request.session_id,
            "message": request.message,
            "user_id": current_user.email,
            "project": "kohtravel",
            "context": enhanced_context
        }
        
        # Get agent infrastructure URL
        agent_url = os.getenv("AGENT_INFRASTRUCTURE_URL", "http://localhost:8001")
        
        # Forward to agent infrastructure with enhanced context
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{agent_url}/api/agent/chat/stream",
                json=agent_request,
                timeout=120.0
            )
            
            if not response.is_success:
                logger.error("Agent infrastructure error", 
                           status_code=response.status_code,
                           response_text=response.text)
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Agent infrastructure error: {response.text}"
                )
            
            # Stream the response back to frontend
            async def generate():
                async for chunk in response.aiter_bytes():
                    yield chunk
                    
            return StreamingResponse(
                generate(),
                media_type=response.headers.get("content-type", "text/plain"),
                headers={"Cache-Control": "no-cache"}
            )
            
    except httpx.TimeoutException:
        logger.error("Agent infrastructure timeout", user_id=current_user.email)
        raise HTTPException(status_code=504, detail="Agent service timeout")
    except Exception as e:
        logger.error("Chat with context failed", error=str(e), user_id=current_user.email)
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")