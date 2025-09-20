"""
Main FastAPI application for agent infrastructure
"""
from contextlib import asynccontextmanager
from typing import Dict, Any
import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.server.routes.agent import router as agent_router
from src.server.routes.agents import router as agents_router
from src.server.routes.health import router as health_router
from src.server.routes.init import router as init_router
from src.server.routes.cleanup import router as cleanup_router
from src.server.middleware.auth import AuthMiddleware
from src.server.middleware.logging import LoggingMiddleware
from src.config.settings import get_settings
from src.core.logging_config import configure_logging
from src.database import db_manager, ensure_database_initialized

logger = structlog.get_logger(__name__)

# Global app state
app_state: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    settings = get_settings()

    # Configure production logging
    configure_logging(
        log_level=settings.log_level,
        log_dir="logs",
        enable_json=True,
        enable_file_rotation=True
    )

    logger.info("Starting agent infrastructure server", version="0.1.0")

    # Initialize Agent OS database (required for operation)
    try:
        await ensure_database_initialized()
        if settings.agent_os_enabled:
            logger.info("Agent OS database initialized successfully")
        else:
            logger.error("Agent OS database is disabled but required for operation")
            raise RuntimeError("Agent OS database must be enabled for operation")
    except Exception as e:
        logger.error("Failed to initialize Agent OS database", error=str(e))
        logger.error("Database is required for operation - cannot start without database connectivity")
        raise RuntimeError(f"Database initialization failed: {e}") from e

    # Store settings in app state
    app_state["settings"] = settings

    yield

    # Shutdown
    logger.info("Shutting down agent infrastructure server")

    # Close database connections
    try:
        await db_manager.close()
        logger.info("Agent OS database connections closed")
    except Exception as e:
        logger.error("Error closing database connections", error=str(e))


def create_app() -> FastAPI:
    """Create FastAPI application"""
    
    app = FastAPI(
        title="Agent Infrastructure",
        description="Standalone agent infrastructure for multi-project AI agent management",
        version="0.1.0",
        lifespan=lifespan
    )
    
    # Add middleware
    settings = get_settings()
    
    # CORS middleware - Smart DevOps approach (same as main API)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://localhost:[3-8][0-9]{3}$|.*\.vercel\.app$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Custom middleware
    app.add_middleware(LoggingMiddleware)
    
    # Add auth middleware if enabled
    if settings.auth_enabled:
        app.add_middleware(AuthMiddleware)
    
    # Include routers
    app.include_router(health_router, prefix="/health", tags=["health"])
    app.include_router(agents_router, tags=["Agent Management"])  # New Agent Management API
    app.include_router(init_router, prefix="/api/agent", tags=["agent-init"])
    app.include_router(agent_router, prefix="/api/agent", tags=["agent"])  # Legacy agent endpoints
    app.include_router(cleanup_router, prefix="/api/agent", tags=["agent-cleanup"])
    
    return app


def run_server(host: str = "0.0.0.0", port: int = 8001, reload: bool = False):
    """Run the agent server"""
    uvicorn.run(
        "src.server.main:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_config=None  # Use structlog configuration
    )


if __name__ == "__main__":
    import sys
    
    # Default values
    host = "0.0.0.0"
    port = 8001
    reload = False
    
    # Parse simple command line arguments
    if len(sys.argv) > 1:
        if "--reload" in sys.argv:
            reload = True
        if "--port" in sys.argv:
            port_idx = sys.argv.index("--port") + 1
            if port_idx < len(sys.argv):
                port = int(sys.argv[port_idx])
        if "--host" in sys.argv:
            host_idx = sys.argv.index("--host") + 1
            if host_idx < len(sys.argv):
                host = sys.argv[host_idx]
    
    run_server(host=host, port=port, reload=reload)