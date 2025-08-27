"""
Agent chat endpoint that properly initializes agents with KohTravel prompts
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import structlog
import httpx
from datetime import datetime
import json

from database import get_db
from services.agent_service import kohtravel_agent_service

logger = structlog.get_logger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str
    user_id: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    session_id: str
    status: str
    message: str


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest, db: Session = Depends(get_db)):
    """Chat with KohTravel agent (non-streaming)"""
    try:
        # Ensure agent is initialized for this user
        await kohtravel_agent_service.initialize_agent(request.user_id)
        
        # Send message through agent service
        result = await kohtravel_agent_service.send_message(
            session_id=request.session_id,
            message=request.message,
            user_id=request.user_id,
            context=request.context
        )
        
        return ChatResponse(
            session_id=result["session_id"],
            status=result["status"],
            message=result["message"]
        )
        
    except Exception as e:
        logger.error("Chat error", error=str(e), session_id=request.session_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def stream_chat_with_agent(request: ChatRequest, db: Session = Depends(get_db)):
    """Stream chat with KohTravel agent"""
    
    async def generate_stream():
        try:
            # Ensure agent is initialized for this user
            logger.info("Initializing KohTravel agent", user_id=request.user_id)
            init_success = await kohtravel_agent_service.initialize_agent(request.user_id)
            logger.info("Agent initialization result", user_id=request.user_id, success=init_success)
            
            # Stream the conversation through agent infrastructure
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    'POST',
                    "http://localhost:8001/api/agent/chat/stream",
                    json={
                        "session_id": request.session_id,
                        "message": request.message,
                        "project": "kohtravel",
                        "user_id": request.user_id,
                        "context": request.context
                    }
                ) as response:
                    if response.status_code != 200:
                        yield f'data: {{"type": "error", "data": {{"error": "Chat stream failed"}}}}\n\n'
                        return
                        
                    async for chunk in response.aiter_text():
                        if chunk.strip():
                            yield chunk
                            
        except Exception as e:
            logger.error("Stream chat error", error=str(e), session_id=request.session_id)
            yield f'data: {{"type": "error", "data": {{"error": "{str(e)}"}}}}\n\n'
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )