"""
Database connection and session management for Agent OS
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy.pool import QueuePool
from typing import AsyncGenerator, Optional
import structlog
from src.config.settings import get_settings

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """
    Manages database connections and session lifecycle for Agent OS

    Features:
    - Async SQLAlchemy 2.0+ engine management
    - Connection pooling with configurable parameters
    - Graceful initialization and cleanup
    - Health checking and monitoring
    """

    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_maker: Optional[async_sessionmaker[AsyncSession]] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database engine and session maker"""
        if self._initialized:
            logger.debug("Database already initialized")
            return

        settings = get_settings()

        if not settings.agent_os_enabled:
            logger.info("Agent OS database disabled via configuration")
            return

        if not settings.agent_os_database_url:
            logger.warning("Agent OS database URL not configured")
            return

        try:
            self._engine = create_async_engine(
                settings.agent_os_database_url,
                pool_size=settings.agent_os_pool_size,
                max_overflow=settings.agent_os_max_overflow,
                pool_timeout=settings.agent_os_pool_timeout,
                pool_recycle=settings.agent_os_pool_recycle,
                poolclass=QueuePool,
                echo=settings.debug,
                echo_pool=settings.debug,
            )

            self._session_maker = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            self._initialized = True
            logger.info(
                "Agent OS database initialized successfully",
                pool_size=settings.agent_os_pool_size,
                max_overflow=settings.agent_os_max_overflow,
                pool_timeout=settings.agent_os_pool_timeout,
                pool_recycle=settings.agent_os_pool_recycle
            )

        except Exception as e:
            logger.error("Failed to initialize Agent OS database", error=str(e))
            raise

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with proper cleanup"""
        if not self._initialized or not self._session_maker:
            raise RuntimeError("Agent OS database not initialized")

        async with self._session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def health_check(self) -> bool:
        """Check database connectivity and health"""
        if not self._initialized or not self._engine:
            return False

        try:
            async with self._engine.begin() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    @property
    def is_initialized(self) -> bool:
        """Check if database manager is initialized"""
        return self._initialized

    @property
    def engine(self) -> Optional[AsyncEngine]:
        """Get the database engine (for advanced usage)"""
        return self._engine

    async def close(self) -> None:
        """Close database connections and cleanup resources"""
        if self._engine:
            await self._engine.dispose()
            logger.info("Agent OS database connections closed")

        self._engine = None
        self._session_maker = None
        self._initialized = False


# Global database manager instance
db_manager = DatabaseManager()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for getting database session

    This function is designed to be used as a FastAPI dependency
    or in any async context where a database session is needed.

    Yields:
        AsyncSession: Database session with automatic cleanup
    """
    async for session in db_manager.get_session():
        yield session


async def ensure_database_initialized() -> None:
    """
    Ensure database is initialized, initialize if needed

    This is a convenience function that can be called from
    application startup to ensure database connectivity.
    """
    if not db_manager.is_initialized:
        await db_manager.initialize()