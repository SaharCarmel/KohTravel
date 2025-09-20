"""
Test configuration and fixtures for Agent Infrastructure tests.

This module provides shared pytest fixtures and configuration for all test suites.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any

from src.schemas.tool_schemas import (
    ToolDefinition, ToolRegistrationRequest, ToolType, ToolStatus,
    ToolHealthStatus, SecurityLevel, ToolSecurityPolicy
)
from src.core.tool_registry import ToolRegistryCore
from src.config.settings import Settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.agent_os_enabled = True
    settings.dynamic_tool_management_enabled = True
    settings.tool_health_monitoring_enabled = True
    settings.allowed_tool_domains = ["localhost", "127.0.0.1", "testapi.com"]
    settings.anthropic_api_key = "test-api-key"
    settings.default_model = "claude-3-5-sonnet-20241022"
    settings.allowed_file_paths = ["/tmp", "/test"]
    settings.allow_file_write = True
    return settings


@pytest.fixture
def sample_tool_registration():
    """Sample tool registration request for testing."""
    return ToolRegistrationRequest(
        name="test_tool",
        type=ToolType.EXTERNAL,
        description="Test tool for unit testing",
        endpoint_url="http://localhost:8080/test-tool",
        security_policy=ToolSecurityPolicy(
            security_level=SecurityLevel.MEDIUM,
            allowed_domains=["localhost"],
            timeout_seconds=30
        ),
        enabled=True,
        tags=["test", "external"],
        version="1.0.0"
    )


@pytest.fixture
def sample_tool_definition():
    """Sample tool definition for testing."""
    return ToolDefinition(
        id="test_tool_123",
        agent_id="test_agent_456",
        name="test_tool",
        type=ToolType.EXTERNAL,
        description="Test tool for unit testing",
        endpoint_url="http://localhost:8080/test-tool",
        security_policy=ToolSecurityPolicy(),
        status=ToolStatus.ACTIVE,
        health=ToolHealthStatus.HEALTHY,
        enabled=True,
        tags=["test"],
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
async def tool_registry():
    """Tool registry instance for testing."""
    registry = ToolRegistryCore()
    # Initialize without database session for unit tests
    await registry.initialize()
    yield registry
    # Cleanup
    await registry.shutdown()


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for testing external requests."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_database_session():
    """Mock database session for testing."""
    session = AsyncMock()
    return session


@pytest.fixture
def sample_agent_data():
    """Sample agent data for testing."""
    return {
        "id": "test_agent_123",
        "app_name": "test_app",
        "name": "Test Agent",
        "description": "Test agent for unit testing",
        "base_system_prompt": "You are a test assistant.",
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4096,
        "temperature": 0.0,
        "is_active": True,
        "tools_config": {
            "test_tool": {
                "type": "external",
                "endpoint_url": "http://localhost:8080/test-tool"
            }
        },
        "enabled_tools": ["test_tool"]
    }


@pytest.fixture
def sample_api_responses():
    """Sample API responses for testing."""
    return {
        "health_check": {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "0.1.0",
            "service": "agent-infrastructure",
            "database": {
                "enabled": True,
                "connected": True,
                "features": {
                    "session_persistence": True,
                    "agent_persistence": True,
                    "user_context_persistence": True
                }
            }
        },
        "agent_list": {
            "agents": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
            "total_pages": 0
        }
    }


# Unit test helper functions

def create_test_tool_definition(**overrides) -> ToolDefinition:
    """Helper function to create test tool definitions with overrides."""
    defaults = {
        "id": "test_tool_123",
        "agent_id": "test_agent_456",
        "name": "test_tool",
        "type": ToolType.EXTERNAL,
        "description": "Test tool",
        "endpoint_url": "http://localhost:8080/test",
        "security_policy": ToolSecurityPolicy(),
        "status": ToolStatus.ACTIVE,
        "health": ToolHealthStatus.HEALTHY,
        "enabled": True,
        "tags": ["test"],
        "version": "1.0.0",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    defaults.update(overrides)
    return ToolDefinition.model_validate(defaults)


def create_test_tool_registration(**overrides) -> ToolRegistrationRequest:
    """Helper function to create test tool registration requests with overrides."""
    defaults = {
        "name": "test_tool",
        "type": ToolType.EXTERNAL,
        "description": "Test tool",
        "endpoint_url": "http://localhost:8080/test",
        "security_policy": ToolSecurityPolicy(),
        "enabled": True,
        "tags": ["test"],
        "version": "1.0.0"
    }
    defaults.update(overrides)
    return ToolRegistrationRequest.model_validate(defaults)


# Integration test helpers

@pytest.fixture
async def test_client():
    """FastAPI test client for integration tests."""
    from httpx import AsyncClient, ASGITransport
    from src.server.main import create_app

    app = create_app()
    # Use ASGITransport to connect AsyncClient to FastAPI app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def database_url():
    """Test database URL."""
    return "postgresql+asyncpg://test_user:test_pass@localhost:5433/test_agent_os"


# Performance test fixtures

@pytest.fixture
def performance_metrics():
    """Structure for collecting performance metrics during tests."""
    return {
        "tool_registration_times": [],
        "cache_hit_times": [],
        "health_check_times": [],
        "api_response_times": []
    }