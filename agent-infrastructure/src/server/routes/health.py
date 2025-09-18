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
    """Basic health check endpoint with database status"""
    settings = get_settings()

    # Check database status
    database_status = None
    overall_status = "healthy"

    if settings.agent_os_database_url:
        try:
            db_connected = await db_manager.health_check()
            database_status = DatabaseStatus(
                enabled=settings.agent_os_enabled,
                connected=db_connected,
                features={
                    "session_persistence": settings.enable_session_persistence,
                    "agent_persistence": settings.enable_agent_persistence,
                    "user_context_persistence": settings.enable_user_context_persistence
                }
            )

            # If database is enabled but not connected, mark as degraded
            if settings.agent_os_enabled and not db_connected:
                overall_status = "degraded"

        except Exception:
            database_status = DatabaseStatus(
                enabled=settings.agent_os_enabled,
                connected=False,
                features={}
            )
            if settings.agent_os_enabled:
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
    """Detailed database status endpoint"""
    settings = get_settings()

    if not settings.agent_os_database_url:
        return {
            "enabled": False,
            "message": "Agent OS database not configured"
        }

    try:
        connected = await db_manager.health_check()
        return {
            "enabled": settings.agent_os_enabled,
            "connected": connected,
            "initialized": db_manager.is_initialized,
            "features": {
                "session_persistence": settings.enable_session_persistence,
                "agent_persistence": settings.enable_agent_persistence,
                "user_context_persistence": settings.enable_user_context_persistence
            },
            "configuration": {
                "pool_size": settings.agent_os_pool_size,
                "max_overflow": settings.agent_os_max_overflow,
                "pool_timeout": settings.agent_os_pool_timeout,
                "pool_recycle": settings.agent_os_pool_recycle
            }
        }
    except Exception as e:
        return {
            "enabled": settings.agent_os_enabled,
            "connected": False,
            "error": str(e)
        }