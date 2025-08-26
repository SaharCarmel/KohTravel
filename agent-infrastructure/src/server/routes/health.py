"""
Health check routes
"""
from datetime import datetime
from fastapi import APIRouter, Response
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    service: str


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="0.1.0",
        service="agent-infrastructure"
    )


@router.get("/ready")
async def readiness_check():
    """Readiness check for k8s/docker"""
    return {"status": "ready", "timestamp": datetime.utcnow()}


@router.get("/live") 
async def liveness_check():
    """Liveness check for k8s/docker"""
    return {"status": "alive", "timestamp": datetime.utcnow()}