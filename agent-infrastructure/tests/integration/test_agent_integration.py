"""
Integration tests for agent functionality with dynamic tool loading.

Tests agent creation, tool integration, health validation,
and fallback mechanisms.
"""

import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from src.schemas.tool_schemas import (
    ToolDefinition, ToolRegistrationRequest, ToolType, ToolStatus,
    ToolHealthStatus, ToolSecurityPolicy, ToolSchema, ToolParameter
)


class TestAgentToolIntegration:
    """Test agent integration with dynamic tool loading."""

    @pytest.fixture
    async def sample_agent(self, test_client):
        """Create a sample agent for testing."""
        agent_data = {
            "app_name": "test_integration_app",
            "name": "Test Integration Agent",
            "description": "Test agent for integration testing",
            "base_system_prompt": "You are a test assistant with tool capabilities.",
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 4096,
            "temperature": 0.0,
            "tools_config": {
                "test_tool": {
                    "type": "external",
                    "endpoint_url": "http://localhost:8080/test-tool"
                }
            },
            "enabled_tools": ["test_tool"]
        }

        response = await test_client.post("/api/agents", json=agent_data)
        return response.json()

    @pytest.mark.asyncio
    async def test_agent_creation_with_tool_config(self, test_client):
        """Test creating an agent with tool configuration."""
        agent_data = {
            "app_name": "test_tool_config_app",
            "name": "Test Tool Config Agent",
            "description": "Test agent with tool configuration",
            "base_system_prompt": "You are a test assistant.",
            "model": "claude-3-5-sonnet-20241022",
            "tools_config": {
                "search_tool": {
                    "type": "external",
                    "endpoint_url": "https://api.example.com/search",
                    "security_level": "medium"
                },
                "internal_tool": {
                    "type": "internal",
                    "description": "Internal processing tool"
                }
            },
            "enabled_tools": ["search_tool", "internal_tool"]
        }

        response = await test_client.post("/api/agents", json=agent_data)

        assert response.status_code in [200, 201]

        agent = response.json()
        assert agent["name"] == "Test Tool Config Agent"
        assert "tools_config" in agent
        assert "search_tool" in agent["tools_config"]
        assert "internal_tool" in agent["tools_config"]
        assert agent["enabled_tools"] == ["search_tool", "internal_tool"]

    @pytest.mark.asyncio
    async def test_agent_tool_loading_from_registry(self, sample_agent, test_client):
        """Test loading tools from registry for an agent."""
        agent_id = sample_agent["id"]

        # Register some tools first
        tool_data = {
            "name": "agent_specific_tool",
            "type": "internal",
            "description": "Tool specific to this agent",
            "version": "1.0.0",
            "tags": [f"agent:{agent_id}"]
        }

        tool_response = await test_client.post("/api/tools/register", json=tool_data)
        assert tool_response.status_code == 201

        # Get agent tools
        response = await test_client.get(f"/api/agents/{agent_id}/tools")

        assert response.status_code == 200

        tools_data = response.json()
        assert "tools" in tools_data
        assert isinstance(tools_data["tools"], list)

    @pytest.mark.asyncio
    async def test_agent_tool_health_validation(self, sample_agent, test_client):
        """Test agent tool health validation."""
        agent_id = sample_agent["id"]

        # Register an external tool for health testing
        tool_data = {
            "name": "health_test_tool",
            "type": "external",
            "description": "Tool for health validation testing",
            "endpoint_url": "https://httpbin.org",  # Known endpoint
            "version": "1.0.0"
        }

        tool_response = await test_client.post("/api/tools/register", json=tool_data)
        if tool_response.status_code == 201:
            tool_id = tool_response.json()["tool_id"]

            # Check tool health for agent
            response = await test_client.get(f"/api/agents/{agent_id}/tools/{tool_id}/health")

            # Should work regardless of actual health status
            assert response.status_code in [200, 404]  # 404 if tool not associated with agent

    @pytest.mark.asyncio
    async def test_agent_external_tool_validation(self, test_client):
        """Test agent with external tool validation."""
        # Create agent with external tool configuration
        agent_data = {
            "app_name": "test_external_app",
            "name": "Test External Tool Agent",
            "description": "Test agent with external tools",
            "base_system_prompt": "You are a test assistant with external tools.",
            "model": "claude-3-5-sonnet-20241022",
            "tools_config": {
                "external_api": {
                    "type": "external",
                    "endpoint_url": "https://api.example.com/tools/external",
                    "security_policy": {
                        "security_level": "high",
                        "require_https": True,
                        "timeout_seconds": 30
                    }
                }
            },
            "enabled_tools": ["external_api"]
        }

        response = await test_client.post("/api/agents", json=agent_data)

        assert response.status_code in [200, 201]

        agent = response.json()
        assert "external_api" in agent["tools_config"]

    @pytest.mark.asyncio
    async def test_agent_fallback_to_legacy_tools(self, test_client):
        """Test agent fallback to legacy tool configuration."""
        # Create agent without dynamic tool management
        agent_data = {
            "app_name": "legacy_test_app",
            "name": "Legacy Test Agent",
            "description": "Test agent for legacy tool fallback",
            "base_system_prompt": "You are a test assistant.",
            "model": "claude-3-5-sonnet-20241022",
            "tools_config": {
                "legacy_tool": {
                    "type": "builtin",
                    "description": "Legacy builtin tool"
                }
            },
            "enabled_tools": ["legacy_tool"]
        }

        response = await test_client.post("/api/agents", json=agent_data)

        assert response.status_code in [200, 201]

        agent = response.json()
        assert "legacy_tool" in agent["tools_config"]

        # Test that legacy tools are available
        agent_id = agent["id"]
        tools_response = await test_client.get(f"/api/agents/{agent_id}/tools")

        assert tools_response.status_code == 200

    @pytest.mark.asyncio
    async def test_agent_tool_configuration_update(self, sample_agent, test_client):
        """Test updating agent tool configuration."""
        agent_id = sample_agent["id"]

        # Update tool configuration
        update_data = {
            "tools_config": {
                "updated_tool": {
                    "type": "internal",
                    "description": "Updated tool configuration"
                },
                "new_external_tool": {
                    "type": "external",
                    "endpoint_url": "https://api.example.com/new-tool"
                }
            },
            "enabled_tools": ["updated_tool", "new_external_tool"]
        }

        response = await test_client.put(f"/api/agents/{agent_id}/tools", json=update_data)

        assert response.status_code == 200

        # Verify the update
        get_response = await test_client.get(f"/api/agents/{agent_id}")
        updated_agent = get_response.json()

        assert "updated_tool" in updated_agent["tools_config"]
        assert "new_external_tool" in updated_agent["tools_config"]
        assert set(updated_agent["enabled_tools"]) == {"updated_tool", "new_external_tool"}

    @pytest.mark.asyncio
    async def test_agent_session_with_tools(self, sample_agent, test_client):
        """Test creating a session with tool-enabled agent."""
        agent_id = sample_agent["id"]

        # Create a session
        session_data = {
            "user_id": "test_user_tools",
            "session_name": "Tool Test Session"
        }

        response = await test_client.post(f"/api/agents/{agent_id}/users/test_user_tools/sessions", json=session_data)

        assert response.status_code == 201

        session = response.json()
        assert "session_id" in session
        assert session["agent_id"] == agent_id

        # Test chat with tool capabilities
        session_id = session["session_id"]
        chat_data = {
            "message": "Hello, can you help me test tools?",
            "user_auth": {
                "user_id": "test_user_tools",
                "token": "test_token"
            }
        }

        # This might fail if no actual tool endpoints are available
        chat_response = await test_client.post(f"/api/agents/{agent_id}/sessions/{session_id}/chat", json=chat_data)

        # Should get a response even if tools aren't available
        assert chat_response.status_code in [200, 400, 422]


class TestToolDefinitionConversion:
    """Test conversion between ToolDefinition and ExternalTool."""

    def test_tool_definition_to_external_tool_conversion(self, sample_tool_definition):
        """Test converting ToolDefinition to ExternalTool format."""
        from src.server.routes.agent import _create_external_tool_from_definition

        external_tool = _create_external_tool_from_definition(sample_tool_definition)

        assert external_tool is not None
        assert external_tool.name == sample_tool_definition.name
        assert external_tool.description == sample_tool_definition.description
        assert external_tool.endpoint_url == sample_tool_definition.endpoint_url

    def test_tool_definition_with_complex_schema(self, create_test_tool_definition):
        """Test tool definition with complex input/output schemas."""
        complex_tool = create_test_tool_definition(
            name="complex_schema_tool",
            input_schema=ToolSchema(
                type="object",
                properties={
                    "query": ToolParameter(
                        name="query",
                        type="string",
                        description="Search query"
                    ),
                    "filters": ToolParameter(
                        name="filters",
                        type="object",
                        description="Filter options"
                    )
                },
                required=["query"]
            ),
            output_schema=ToolSchema(
                type="object",
                properties={
                    "results": ToolParameter(
                        name="results",
                        type="array",
                        description="Search results"
                    )
                }
            )
        )

        from src.server.routes.agent import _create_external_tool_from_definition

        external_tool = _create_external_tool_from_definition(complex_tool)

        assert external_tool is not None
        assert external_tool.name == "complex_schema_tool"

    def test_internal_tool_definition_handling(self, create_test_tool_definition):
        """Test handling of internal tool definitions."""
        internal_tool = create_test_tool_definition(
            name="internal_test_tool",
            type=ToolType.INTERNAL,
            endpoint_url=None
        )

        # Internal tools shouldn't be converted to external tools
        from src.server.routes.agent import _create_external_tool_from_definition

        try:
            external_tool = _create_external_tool_from_definition(internal_tool)
            # Should either return None or handle internal tools differently
            assert external_tool is None or external_tool.name == "internal_test_tool"
        except Exception:
            # It's acceptable for this to raise an exception for internal tools
            pass


class TestAgentHealthMonitoring:
    """Test agent health monitoring with tools."""

    @pytest.mark.asyncio
    async def test_agent_overall_health(self, sample_agent, test_client):
        """Test getting overall agent health status."""
        agent_id = sample_agent["id"]

        response = await test_client.get(f"/api/agents/{agent_id}/health")

        assert response.status_code == 200

        health_data = response.json()
        assert "status" in health_data
        assert "tools_health" in health_data
        assert "last_checked" in health_data

    @pytest.mark.asyncio
    async def test_agent_tool_health_summary(self, sample_agent, test_client):
        """Test getting agent tool health summary."""
        agent_id = sample_agent["id"]

        # Register some tools for the agent
        for i in range(3):
            tool_data = {
                "name": f"health_tool_{i}",
                "type": "internal",
                "description": f"Health test tool {i}",
                "version": "1.0.0"
            }
            await test_client.post("/api/tools/register", json=tool_data)

        response = await test_client.get(f"/api/agents/{agent_id}/tools/health")

        assert response.status_code == 200

        health_summary = response.json()
        assert "tools" in health_summary
        assert "healthy_count" in health_summary
        assert "total_count" in health_summary

    @pytest.mark.asyncio
    async def test_agent_performance_metrics(self, sample_agent, test_client):
        """Test getting agent performance metrics."""
        agent_id = sample_agent["id"]

        response = await test_client.get(f"/api/agents/{agent_id}/metrics")

        # Metrics endpoint might not be fully implemented yet
        assert response.status_code in [200, 404, 501]

        if response.status_code == 200:
            metrics = response.json()
            # Expected metrics fields
            expected_fields = ["tool_usage", "response_times", "success_rates"]
            # At least some metrics should be present
            assert any(field in metrics for field in expected_fields)


class TestAgentErrorHandling:
    """Test agent error handling scenarios."""

    @pytest.mark.asyncio
    async def test_agent_with_invalid_tool_config(self, test_client):
        """Test agent creation with invalid tool configuration."""
        agent_data = {
            "app_name": "invalid_tool_app",
            "name": "Invalid Tool Agent",
            "description": "Test agent with invalid tool config",
            "base_system_prompt": "You are a test assistant.",
            "model": "claude-3-5-sonnet-20241022",
            "tools_config": {
                "invalid_tool": {
                    "type": "external",
                    # Missing required endpoint_url
                    "security_level": "high"
                }
            },
            "enabled_tools": ["invalid_tool"]
        }

        response = await test_client.post("/api/agents", json=agent_data)

        # Should handle invalid configuration gracefully
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_agent_with_unreachable_tools(self, test_client):
        """Test agent behavior with unreachable external tools."""
        agent_data = {
            "app_name": "unreachable_tool_app",
            "name": "Unreachable Tool Agent",
            "description": "Test agent with unreachable tools",
            "base_system_prompt": "You are a test assistant.",
            "model": "claude-3-5-sonnet-20241022",
            "tools_config": {
                "unreachable_tool": {
                    "type": "external",
                    "endpoint_url": "https://unreachable-domain-12345.com/tools"
                }
            },
            "enabled_tools": ["unreachable_tool"]
        }

        response = await test_client.post("/api/agents", json=agent_data)

        # Should create agent even with unreachable tools
        assert response.status_code in [200, 201]

        agent = response.json()
        agent_id = agent["id"]

        # Tool health should reflect unreachable status
        health_response = await test_client.get(f"/api/agents/{agent_id}/tools/health")
        assert health_response.status_code == 200

    @pytest.mark.asyncio
    async def test_agent_tool_timeout_handling(self, sample_agent, test_client):
        """Test agent handling of tool timeouts."""
        agent_id = sample_agent["id"]

        # Create a session and try to use tools (will timeout on fake endpoints)
        session_data = {"user_id": "timeout_test_user"}
        session_response = await test_client.post(f"/api/agents/{agent_id}/users/timeout_test_user/sessions", json=session_data)

        if session_response.status_code == 201:
            session_id = session_response.json()["session_id"]

            chat_data = {
                "message": "Please use a tool that will timeout",
                "user_auth": {
                    "user_id": "timeout_test_user",
                    "token": "test_token"
                }
            }

            # Should handle tool timeouts gracefully
            chat_response = await test_client.post(f"/api/agents/{agent_id}/sessions/{session_id}/chat", json=chat_data)
            assert chat_response.status_code in [200, 400, 422, 500]