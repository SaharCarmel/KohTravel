"""
Health check routes
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Response, HTTPException
from pydantic import BaseModel

from src.config.settings import get_settings
from src.database import db_manager

router = APIRouter()


class DatabaseStatus(BaseModel):
    enabled: bool
    connected: bool
    features: Dict[str, bool]


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    service: str
    database: Optional[DatabaseStatus] = None


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    settings = get_settings()

    # Check database status if enabled
    database_status = None
    overall_status = "healthy"

    if settings.agent_os_enabled:
        try:
            db_connected = await db_manager.health_check()
            database_status = DatabaseStatus(
                enabled=True,
                connected=db_connected,
                features={
                    "session_persistence": settings.enable_session_persistence,
                    "agent_persistence": settings.enable_agent_persistence,
                    "user_context_persistence": settings.enable_user_context_persistence
                }
            )
            if not db_connected:
                overall_status = "degraded"
        except Exception:
            database_status = DatabaseStatus(enabled=True, connected=False, features={})
            overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        version="0.1.0",
        service="agent-infrastructure",
        database=database_status
    )


@router.get("/ready")
async def readiness_check():
    """Readiness check for k8s/docker"""
    settings = get_settings()

    # Service is ready if either database is working or persistence is disabled
    ready = True
    if settings.agent_os_enabled:
        try:
            ready = await db_manager.health_check()
        except Exception:
            ready = False

    if not ready:
        raise HTTPException(status_code=503, detail="Service not ready")

    return {"status": "ready", "timestamp": datetime.now(timezone.utc)}


@router.get("/live")
async def liveness_check():
    """Liveness check for k8s/docker"""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc)}


@router.get("/database")
async def database_status():
    """Database status endpoint"""
    settings = get_settings()

    if not settings.agent_os_database_url:
        return {"enabled": False, "connected": False}

    try:
        connected = await db_manager.health_check()
        return {
            "enabled": settings.agent_os_enabled,
            "connected": connected,
            "initialized": db_manager.is_initialized
        }
    except Exception:
        return {"enabled": settings.agent_os_enabled, "connected": False}