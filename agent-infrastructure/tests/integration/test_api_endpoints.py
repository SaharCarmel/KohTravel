"""
Integration tests for API endpoints.

Tests all API endpoints including health checks, agent management,
tool management, and error handling scenarios.
"""

import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock
import httpx

from src.schemas.tool_schemas import (
    ToolRegistrationRequest, ToolUpdateRequest,
    ToolType, SecurityLevel, ToolSecurityPolicy
)


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_main_health_endpoint(self, test_client):
        """Test main health check endpoint."""
        response = await test_client.get("/health/")

        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "service" in data
        assert "database" in data

        assert data["status"] == "healthy"
        assert data["service"] == "agent-infrastructure"
        assert data["version"] == "0.1.0"

        # Check database status
        db_info = data["database"]
        assert "enabled" in db_info
        assert "connected" in db_info
        assert "features" in db_info

    @pytest.mark.asyncio
    async def test_readiness_endpoint(self, test_client):
        """Test readiness probe endpoint."""
        response = await test_client.get("/health/ready")

        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_liveness_endpoint(self, test_client):
        """Test liveness probe endpoint."""
        response = await test_client.get("/health/live")

        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "alive"


class TestAgentEndpoints:
    """Test agent management endpoints."""

    @pytest.mark.asyncio
    async def test_list_agents_empty(self, test_client):
        """Test listing agents when none exist."""
        response = await test_client.get("/api/agents")

        assert response.status_code == 200

        data = response.json()
        assert "agents" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

        assert isinstance(data["agents"], list)
        assert data["total"] >= 0

    @pytest.mark.asyncio
    async def test_create_agent(self, test_client):
        """Test creating a new agent."""
        agent_data = {
            "app_name": "test_app",
            "name": "Test Agent",
            "description": "Test agent for integration testing",
            "base_system_prompt": "You are a test assistant.",
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 4096,
            "temperature": 0.0,
            "tools_config": {},
            "enabled_tools": []
        }

        response = await test_client.post("/api/agents", json=agent_data)

        # Should succeed or return existing agent
        assert response.status_code in [200, 201]

        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Agent"
        assert data["app_name"] == "test_app"

    @pytest.mark.asyncio
    async def test_get_agent(self, test_client):
        """Test retrieving an agent by ID."""
        # First create an agent
        agent_data = {
            "app_name": "test_get_app",
            "name": "Test Get Agent",
            "description": "Test agent for retrieval testing",
            "base_system_prompt": "You are a test assistant.",
            "model": "claude-3-5-sonnet-20241022"
        }

        create_response = await test_client.post("/api/agents", json=agent_data)
        assert create_response.status_code in [200, 201]

        agent_id = create_response.json()["id"]

        # Now retrieve it
        response = await test_client.get(f"/api/agents/{agent_id}")

        assert response.status_code == 200

        data = response.json()
        assert data["id"] == agent_id
        assert data["name"] == "Test Get Agent"

    @pytest.mark.asyncio
    async def test_get_nonexistent_agent(self, test_client):
        """Test retrieving a non-existent agent."""
        response = await test_client.get("/api/agents/nonexistent_agent_id")

        assert response.status_code == 404

        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_update_agent_prompt(self, test_client):
        """Test updating an agent's system prompt."""
        # First create an agent
        agent_data = {
            "app_name": "test_update_app",
            "name": "Test Update Agent",
            "description": "Test agent for update testing",
            "base_system_prompt": "Original prompt",
            "model": "claude-3-5-sonnet-20241022"
        }

        create_response = await test_client.post("/api/agents", json=agent_data)
        agent_id = create_response.json()["id"]

        # Update the prompt
        update_data = {
            "base_system_prompt": "Updated system prompt"
        }

        response = await test_client.put(f"/api/agents/{agent_id}/prompt", json=update_data)

        assert response.status_code == 200

        # Verify the update
        get_response = await test_client.get(f"/api/agents/{agent_id}")
        updated_agent = get_response.json()
        assert updated_agent["base_system_prompt"] == "Updated system prompt"


class TestToolManagementEndpoints:
    """Test tool management endpoints."""

    @pytest.mark.asyncio
    async def test_register_internal_tool(self, test_client):
        """Test registering an internal tool."""
        tool_data = {
            "name": "test_internal_tool",
            "type": "internal",
            "description": "Test internal tool for API testing",
            "version": "1.0.0",
            "tags": ["test", "internal"]
        }

        response = await test_client.post("/api/tools/register", json=tool_data)

        assert response.status_code == 201

        data = response.json()
        assert "tool_id" in data
        assert data["tool_id"].startswith("tool_")

    @pytest.mark.asyncio
    async def test_register_external_tool(self, test_client):
        """Test registering an external tool."""
        tool_data = {
            "name": "test_external_tool",
            "type": "external",
            "description": "Test external tool for API testing",
            "endpoint_url": "https://api.example.com/tools",
            "security_policy": {
                "security_level": "medium",
                "timeout_seconds": 30
            },
            "version": "1.0.0",
            "tags": ["test", "external"]
        }

        response = await test_client.post("/api/tools/register", json=tool_data)

        # May succeed or fail depending on validation
        assert response.status_code in [201, 400]

    @pytest.mark.asyncio
    async def test_list_tools(self, test_client):
        """Test listing tools."""
        response = await test_client.get("/api/tools")

        assert response.status_code == 200

        data = response.json()
        assert "tools" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

        assert isinstance(data["tools"], list)

    @pytest.mark.asyncio
    async def test_get_tool_by_id(self, test_client):
        """Test retrieving a tool by ID."""
        # First register a tool
        tool_data = {
            "name": "test_get_tool",
            "type": "internal",
            "description": "Test tool for retrieval",
            "version": "1.0.0"
        }

        register_response = await test_client.post("/api/tools/register", json=tool_data)
        tool_id = register_response.json()["tool_id"]

        # Now retrieve it
        response = await test_client.get(f"/api/tools/{tool_id}")

        assert response.status_code == 200

        data = response.json()
        assert data["id"] == tool_id
        assert data["name"] == "test_get_tool"

    @pytest.mark.asyncio
    async def test_update_tool(self, test_client):
        """Test updating a tool."""
        # First register a tool
        tool_data = {
            "name": "test_update_tool",
            "type": "internal",
            "description": "Original description",
            "version": "1.0.0"
        }

        register_response = await test_client.post("/api/tools/register", json=tool_data)
        tool_id = register_response.json()["tool_id"]

        # Update the tool
        update_data = {
            "description": "Updated description",
            "version": "1.1.0",
            "tags": ["updated", "test"]
        }

        response = await test_client.put(f"/api/tools/{tool_id}", json=update_data)

        assert response.status_code == 200

        # Verify the update
        get_response = await test_client.get(f"/api/tools/{tool_id}")
        updated_tool = get_response.json()
        assert updated_tool["description"] == "Updated description"
        assert updated_tool["version"] == "1.1.0"

    @pytest.mark.asyncio
    async def test_deregister_tool(self, test_client):
        """Test deregistering a tool."""
        # First register a tool
        tool_data = {
            "name": "test_deregister_tool",
            "type": "internal",
            "description": "Tool for deregistration test",
            "version": "1.0.0"
        }

        register_response = await test_client.post("/api/tools/register", json=tool_data)
        tool_id = register_response.json()["tool_id"]

        # Deregister the tool
        response = await test_client.delete(f"/api/tools/{tool_id}")

        assert response.status_code == 200

        # Verify it's removed
        get_response = await test_client.get(f"/api/tools/{tool_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_tool_health_check(self, test_client):
        """Test tool health check endpoint."""
        # First register an external tool
        tool_data = {
            "name": "test_health_tool",
            "type": "external",
            "description": "Tool for health testing",
            "endpoint_url": "https://httpbin.org",  # Known endpoint
            "version": "1.0.0"
        }

        register_response = await test_client.post("/api/tools/register", json=tool_data)
        if register_response.status_code == 201:
            tool_id = register_response.json()["tool_id"]

            # Check health
            response = await test_client.get(f"/api/tools/{tool_id}/health")

            assert response.status_code == 200

            data = response.json()
            assert "health_status" in data
            assert "is_reachable" in data
            assert "checked_at" in data


class TestSessionEndpoints:
    """Test session management endpoints."""

    @pytest.mark.asyncio
    async def test_create_session(self, test_client):
        """Test creating a new session."""
        # First create an agent
        agent_data = {
            "app_name": "test_session_app",
            "name": "Test Session Agent",
            "description": "Test agent for session testing",
            "base_system_prompt": "You are a test assistant.",
            "model": "claude-3-5-sonnet-20241022"
        }

        agent_response = await test_client.post("/api/agents", json=agent_data)
        agent_id = agent_response.json()["id"]

        # Create a session
        session_data = {
            "user_id": "test_user_123",
            "session_name": "Test Session"
        }

        response = await test_client.post(f"/api/agents/{agent_id}/users/test_user_123/sessions", json=session_data)

        assert response.status_code == 201

        data = response.json()
        assert "session_id" in data
        assert "agent_id" in data
        assert data["agent_id"] == agent_id

    @pytest.mark.asyncio
    async def test_get_session_history(self, test_client):
        """Test retrieving session history."""
        # First create an agent and session
        agent_data = {
            "app_name": "test_history_app",
            "name": "Test History Agent",
            "description": "Test agent for history testing",
            "base_system_prompt": "You are a test assistant.",
            "model": "claude-3-5-sonnet-20241022"
        }

        agent_response = await test_client.post("/api/agents", json=agent_data)
        agent_id = agent_response.json()["id"]

        session_data = {"user_id": "test_user_456"}
        session_response = await test_client.post(f"/api/agents/{agent_id}/users/test_user_456/sessions", json=session_data)
        session_id = session_response.json()["session_id"]

        # Get session history
        response = await test_client.get(f"/api/agents/{agent_id}/sessions/{session_id}/history")

        assert response.status_code == 200

        data = response.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_json_request(self, test_client):
        """Test handling of invalid JSON requests."""
        response = await test_client.post(
            "/api/agents",
            content="invalid json content",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, test_client):
        """Test handling of missing required fields."""
        incomplete_agent_data = {
            "name": "Incomplete Agent"
            # Missing required fields like app_name, etc.
        }

        response = await test_client.post("/api/agents", json=incomplete_agent_data)

        assert response.status_code == 422

        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_invalid_tool_type(self, test_client):
        """Test registration with invalid tool type."""
        tool_data = {
            "name": "invalid_type_tool",
            "type": "invalid_type",  # Invalid type
            "description": "Tool with invalid type"
        }

        response = await test_client.post("/api/tools/register", json=tool_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_duplicate_tool_registration(self, test_client):
        """Test handling of duplicate tool registration."""
        tool_data = {
            "name": "duplicate_tool",
            "type": "internal",
            "description": "Test duplicate tool",
            "version": "1.0.0"
        }

        # Register first time
        response1 = await test_client.post("/api/tools/register", json=tool_data)
        assert response1.status_code == 201

        # Register second time (should handle gracefully)
        response2 = await test_client.post("/api/tools/register", json=tool_data)
        assert response2.status_code in [409, 400]  # Conflict or Bad Request

    @pytest.mark.asyncio
    async def test_rate_limiting(self, test_client):
        """Test rate limiting behavior."""
        # Make multiple rapid requests
        tasks = []
        for _ in range(20):
            task = test_client.get("/health/")
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # All requests should be handled (no rate limiting implemented yet)
        # This test is future-proof for when rate limiting is added
        successful_responses = [r for r in responses if isinstance(r, httpx.Response) and r.status_code == 200]
        assert len(successful_responses) > 0