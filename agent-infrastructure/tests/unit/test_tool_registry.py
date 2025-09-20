"""
Unit tests for tool registry core functionality.

Tests the core tool registry system including registration, deregistration,
caching, validation, and health monitoring capabilities.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.tool_registry import ToolRegistryCore, CircuitBreaker, ToolValidator, ToolHealthMonitor
from src.schemas.tool_schemas import (
    ToolRegistrationRequest, ToolUpdateRequest, ToolDefinition,
    ToolType, ToolStatus, ToolHealthStatus, SecurityLevel,
    ToolSecurityPolicy, ToolSchema, ToolParameter
)


class TestCircuitBreaker:
    """Test circuit breaker pattern implementation."""

    def test_initial_state(self):
        """Test circuit breaker initial state."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=2)
        assert cb.state == "closed"
        assert not cb.is_open()
        assert cb.failure_count == 0

    def test_failure_recording(self):
        """Test failure recording before threshold."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=2)

        cb.record_failure()
        assert cb.failure_count == 1
        assert cb.state == "closed"

        cb.record_failure()
        assert cb.failure_count == 2
        assert cb.state == "closed"

    def test_threshold_breach(self):
        """Test circuit breaker opens when threshold is reached."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=2)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        assert cb.is_open()

    @pytest.mark.asyncio
    async def test_recovery_timeout(self):
        """Test circuit breaker recovery after timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)  # Short timeout for testing

        # Trigger circuit breaker
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        # Wait for recovery timeout
        await asyncio.sleep(0.15)
        assert not cb.is_open()  # Should be half-open now

    def test_success_recording(self):
        """Test success recording resets failure count."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=2)

        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == "closed"


class TestToolValidator:
    """Test tool validation functionality."""

    @pytest.fixture
    async def validator(self):
        """Create and cleanup tool validator."""
        validator = ToolValidator()
        yield validator
        await validator.close()

    @pytest.mark.asyncio
    async def test_valid_external_tool_validation(self, validator):
        """Test validation of a valid external tool."""
        tool_request = ToolRegistrationRequest(
            name="test_external_tool",
            type=ToolType.EXTERNAL,
            description="Test external tool",
            endpoint_url="https://api.example.com/tools",
            security_policy=ToolSecurityPolicy(
                security_level=SecurityLevel.MEDIUM,
                timeout_seconds=30
            )
        )

        with patch.object(validator, '_check_connectivity', return_value=True):
            result = await validator.validate_tool_registration(tool_request)
            assert result.schema_validation is True
            assert result.security_validation is True

    @pytest.mark.asyncio
    async def test_connectivity_check_failure(self, validator):
        """Test connectivity check failure handling."""
        tool_request = ToolRegistrationRequest(
            name="test_unreachable_tool",
            type=ToolType.EXTERNAL,
            description="Test unreachable tool",
            endpoint_url="https://unreachable-domain-12345.com/tools"
        )

        result = await validator.validate_tool_registration(tool_request)
        assert result.schema_validation is True
        assert result.security_validation is True
        assert result.connectivity_check is False

    def test_invalid_security_policy_validation(self):
        """Test that invalid security policies are caught by Pydantic."""
        with pytest.raises(ValueError, match="Timeout must be between"):
            ToolRegistrationRequest(
                name="test_invalid_tool",
                type=ToolType.EXTERNAL,
                description="Test tool with invalid security",
                endpoint_url="https://api.example.com/tools",
                security_policy=ToolSecurityPolicy(
                    timeout_seconds=500  # Over limit
                )
            )

    @pytest.mark.asyncio
    async def test_internal_tool_validation(self, validator):
        """Test validation of internal tools."""
        tool_request = ToolRegistrationRequest(
            name="test_internal_tool",
            type=ToolType.INTERNAL,
            description="Test internal tool",
            input_schema=ToolSchema(
                type="object",
                properties={
                    "query": ToolParameter(
                        name="query",
                        type="string",
                        description="Search query"
                    )
                },
                required=["query"]
            )
        )

        result = await validator.validate_tool_registration(tool_request)
        assert result.schema_validation is True
        assert result.security_validation is True
        assert result.connectivity_check is True  # Internal tools don't need connectivity check


class TestToolRegistryCore:
    """Test core tool registry functionality."""

    @pytest.fixture
    async def registry(self, mock_settings):
        """Create and cleanup tool registry."""
        with patch('src.core.tool_registry.get_settings', return_value=mock_settings):
            registry = ToolRegistryCore()
            await registry.initialize()
            yield registry
            await registry.shutdown()

    @pytest.mark.asyncio
    async def test_tool_registration(self, registry):
        """Test tool registration functionality."""
        tool_request = ToolRegistrationRequest(
            name="test_internal_tool",
            type=ToolType.INTERNAL,
            description="Test internal tool for validation",
            input_schema=ToolSchema(
                type="object",
                properties={
                    "query": ToolParameter(
                        name="query",
                        type="string",
                        description="Search query"
                    )
                },
                required=["query"]
            ),
            tags=["test", "internal"],
            version="1.0.0"
        )

        tool_id = await registry.register_tool(tool_request)
        assert tool_id.startswith("tool_")

        # Verify tool can be retrieved
        retrieved_tool = await registry.get_tool_by_id(tool_id)
        assert retrieved_tool is not None
        assert retrieved_tool.name == "test_internal_tool"
        assert retrieved_tool.type == ToolType.INTERNAL

    @pytest.mark.asyncio
    async def test_tool_retrieval_by_name(self, registry):
        """Test tool retrieval by name."""
        tool_request = ToolRegistrationRequest(
            name="test_retrieval_tool",
            type=ToolType.INTERNAL,
            description="Test tool for retrieval"
        )

        tool_id = await registry.register_tool(tool_request)

        # Test retrieval by name
        tool_by_name = await registry.get_tool("test_retrieval_tool")
        assert tool_by_name is not None
        assert tool_by_name.id == tool_id

    @pytest.mark.asyncio
    async def test_tool_update(self, registry):
        """Test tool update functionality."""
        # Register a tool
        tool_request = ToolRegistrationRequest(
            name="test_updateable_tool",
            type=ToolType.INTERNAL,
            description="Original description",
            version="1.0.0"
        )

        tool_id = await registry.register_tool(tool_request)

        # Update the tool
        update_request = ToolUpdateRequest(
            description="Updated description",
            version="1.1.0",
            tags=["updated", "test"]
        )

        success = await registry.update_tool(tool_id, update_request)
        assert success is True

        # Verify updates
        updated_tool = await registry.get_tool_by_id(tool_id)
        assert updated_tool.description == "Updated description"
        assert updated_tool.version == "1.1.0"
        assert "updated" in updated_tool.tags

    @pytest.mark.asyncio
    async def test_caching_functionality(self, registry):
        """Test caching mechanisms."""
        tool_request = ToolRegistrationRequest(
            name="test_cache_tool",
            type=ToolType.INTERNAL,
            description="Tool for cache testing"
        )

        tool_id = await registry.register_tool(tool_request)

        # Verify tool is in cache
        assert tool_id in registry.tool_cache
        cached_tool = registry.tool_cache[tool_id]
        assert cached_tool.name == "test_cache_tool"

        # Test cache hit
        retrieved_tool = await registry.get_tool_by_id(tool_id)
        assert retrieved_tool is not None

        # Test cache invalidation on deregistration
        await registry.deregister_tool(tool_id)
        assert tool_id not in registry.tool_cache

    @pytest.mark.asyncio
    async def test_agent_tools_loading(self, registry):
        """Test agent tools loading functionality."""
        agent_id = "test-agent-123"
        tools = await registry.get_agent_tools(agent_id)

        assert isinstance(tools, list)

        # Test caching of agent tools
        cache_key = f"agent_tools:{agent_id}"
        assert cache_key in registry.agent_tools_cache

    @pytest.mark.asyncio
    async def test_tool_health_monitoring(self, registry):
        """Test health monitoring functionality."""
        # Register an external tool for health testing
        external_tool = ToolRegistrationRequest(
            name="test_health_tool",
            type=ToolType.EXTERNAL,
            description="Tool for health monitoring test",
            endpoint_url="https://httpbin.org"
        )

        tool_id = await registry.register_tool(external_tool)

        # Test health check
        health_status = await registry.get_tool_health_status("test_health_tool")
        assert health_status in [
            ToolHealthStatus.HEALTHY,
            ToolHealthStatus.DEGRADED,
            ToolHealthStatus.UNHEALTHY,
            ToolHealthStatus.UNREACHABLE,
            ToolHealthStatus.UNKNOWN
        ]

        # Test health validation
        tool = await registry.get_tool_by_id(tool_id)
        is_healthy = await registry.validate_tool_health(tool)
        assert isinstance(is_healthy, bool)

    @pytest.mark.asyncio
    async def test_tool_deregistration(self, registry):
        """Test tool deregistration."""
        tool_request = ToolRegistrationRequest(
            name="test_deregister_tool",
            type=ToolType.INTERNAL,
            description="Tool for deregistration test"
        )

        tool_id = await registry.register_tool(tool_request)

        # Verify tool exists
        tool = await registry.get_tool_by_id(tool_id)
        assert tool is not None

        # Deregister tool
        success = await registry.deregister_tool(tool_id)
        assert success is True

        # Verify tool is removed
        tool = await registry.get_tool_by_id(tool_id)
        assert tool is None

    @pytest.mark.asyncio
    async def test_error_handling(self, registry):
        """Test error handling scenarios."""
        # Test updating non-existent tool
        update_request = ToolUpdateRequest(description="Updated")
        success = await registry.update_tool("nonexistent_tool_id", update_request)
        assert success is False

        # Test deregistering non-existent tool
        success = await registry.deregister_tool("nonexistent_tool_id")
        assert success is False

        # Test getting non-existent tool
        tool = await registry.get_tool("nonexistent_tool_name")
        assert tool is None


class TestToolHealthMonitor:
    """Test tool health monitoring functionality."""

    @pytest.fixture
    def health_monitor(self):
        """Create health monitor instance."""
        return ToolHealthMonitor()

    @pytest.mark.asyncio
    async def test_health_check_reachable_endpoint(self, health_monitor):
        """Test health check for reachable endpoint."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.1
            mock_get.return_value = mock_response

            result = await health_monitor.check_tool_health("https://api.example.com", "test_tool")

            assert result.health_status == ToolHealthStatus.HEALTHY
            assert result.is_reachable is True
            assert result.response_time_ms == 100.0

    @pytest.mark.asyncio
    async def test_health_check_unreachable_endpoint(self, health_monitor):
        """Test health check for unreachable endpoint."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = await health_monitor.check_tool_health("https://unreachable.com", "test_tool")

            assert result.health_status == ToolHealthStatus.UNREACHABLE
            assert result.is_reachable is False
            assert result.error_message == "Connection failed"

    @pytest.mark.asyncio
    async def test_health_check_degraded_endpoint(self, health_monitor):
        """Test health check for degraded endpoint."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.elapsed.total_seconds.return_value = 2.0
            mock_get.return_value = mock_response

            result = await health_monitor.check_tool_health("https://api.example.com", "test_tool")

            assert result.health_status == ToolHealthStatus.DEGRADED
            assert result.status_code == 500
            assert result.response_time_ms == 2000.0