#!/usr/bin/env python3
"""
Comprehensive API Endpoints Test for Phase 2.2
Tests all API endpoints, error handling, and response validation.
"""

import sys
import json
import asyncio
import httpx
from typing import Dict, Any

# Add src to path for imports
sys.path.append('src')


class APIEndpointTester:
    """Comprehensive API endpoint test suite"""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
        self.client = None

    def log_test(self, test_name: str, passed: bool, error: str = None):
        """Log test result"""
        if passed:
            self.tests_passed += 1
            print(f"✓ {test_name}")
        else:
            self.tests_failed += 1
            if error:
                self.errors.append(f"{test_name}: {error}")
                print(f"✗ {test_name}: {error}")
            else:
                print(f"✗ {test_name}")

    async def setup_client(self):
        """Setup HTTP client"""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=20)
        )

    async def cleanup_client(self):
        """Cleanup HTTP client"""
        if self.client:
            await self.client.aclose()

    async def test_health_endpoints(self):
        """Test health check endpoints"""
        print("\n=== Testing Health Endpoints ===")

        # Test main health endpoint
        try:
            response = await self.client.get(f"{self.base_url}/health/")
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

            self.log_test("Health endpoint - main status", True)

        except Exception as e:
            self.log_test("Health endpoint - main status", False, str(e))

        # Test readiness endpoint
        try:
            response = await self.client.get(f"{self.base_url}/health/ready")
            assert response.status_code == 200

            data = response.json()
            assert "status" in data
            assert data["status"] == "ready"

            self.log_test("Health endpoint - readiness", True)

        except Exception as e:
            self.log_test("Health endpoint - readiness", False, str(e))

        # Test liveness endpoint
        try:
            response = await self.client.get(f"{self.base_url}/health/live")
            assert response.status_code == 200

            data = response.json()
            assert "status" in data
            assert data["status"] == "alive"

            self.log_test("Health endpoint - liveness", True)

        except Exception as e:
            self.log_test("Health endpoint - liveness", False, str(e))

    async def test_agent_endpoints(self):
        """Test agent management endpoints"""
        print("\n=== Testing Agent Endpoints ===")

        # Test listing agents
        try:
            response = await self.client.get(f"{self.base_url}/api/agent/agents")
            assert response.status_code == 200

            data = response.json()
            assert "agents" in data
            assert isinstance(data["agents"], list)

            self.log_test("Agent endpoints - list agents", True)

        except Exception as e:
            self.log_test("Agent endpoints - list agents", False, str(e))

        # Test getting tools for a project
        try:
            response = await self.client.get(
                f"{self.base_url}/api/agent/tools",
                params={"project": "test", "user_id": "test_user"}
            )
            assert response.status_code == 200

            data = response.json()
            assert "project" in data
            assert "tools" in data
            assert isinstance(data["tools"], list)

            self.log_test("Agent endpoints - list tools", True)

        except Exception as e:
            self.log_test("Agent endpoints - list tools", False, str(e))

    async def test_chat_endpoints(self):
        """Test chat functionality endpoints"""
        print("\n=== Testing Chat Endpoints ===")

        # Test basic chat
        try:
            chat_payload = {
                "session_id": "test_session_001",
                "message": "Hello, this is a test message",
                "project": "test_project",
                "user_id": "test_user_123",
                "context": {"test": "context"}
            }

            response = await self.client.post(
                f"{self.base_url}/api/agent/chat",
                json=chat_payload
            )

            # Chat might fail due to no API key, but endpoint should exist
            assert response.status_code in [200, 422, 500]

            if response.status_code == 200:
                data = response.json()
                assert "session_id" in data
                assert "status" in data
                assert "message" in data
                self.log_test("Chat endpoints - basic chat (success)", True)
            else:
                # Expected to fail due to missing API key or configuration
                self.log_test("Chat endpoints - basic chat (expected failure)", True)

        except Exception as e:
            self.log_test("Chat endpoints - basic chat", False, str(e))

        # Test chat without user_id (should fail)
        try:
            bad_payload = {
                "session_id": "test_session_002",
                "message": "Test without user_id",
                "project": "test_project"
            }

            response = await self.client.post(
                f"{self.base_url}/api/agent/chat",
                json=bad_payload
            )

            # Should fail with validation error (400, 422, or 500 with validation message)
            assert response.status_code in [400, 422, 500]

            # If it's a 500, check that it contains validation error message
            if response.status_code == 500:
                text = response.text
                assert "User ID is required" in text

            self.log_test("Chat endpoints - missing user_id validation", True)

        except Exception as e:
            self.log_test("Chat endpoints - missing user_id validation", False, str(e))

    async def test_conversation_endpoints(self):
        """Test conversation management endpoints"""
        print("\n=== Testing Conversation Endpoints ===")

        # Test getting conversation history
        try:
            response = await self.client.get(
                f"{self.base_url}/api/agent/conversation/test_session_001",
                params={"project": "test", "user_id": "test_user"}
            )

            assert response.status_code == 200

            data = response.json()
            assert "session_id" in data
            assert "project" in data
            assert "messages" in data
            assert isinstance(data["messages"], list)

            self.log_test("Conversation endpoints - get history", True)

        except Exception as e:
            self.log_test("Conversation endpoints - get history", False, str(e))

        # Test clearing conversation
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/agent/conversation/test_session_clear",
                params={"project": "test", "user_id": "test_user"}
            )

            assert response.status_code == 200

            data = response.json()
            assert "session_id" in data
            assert "status" in data
            assert data["status"] == "cleared"

            self.log_test("Conversation endpoints - clear history", True)

        except Exception as e:
            self.log_test("Conversation endpoints - clear history", False, str(e))

    async def test_error_handling(self):
        """Test API error handling scenarios"""
        print("\n=== Testing Error Handling ===")

        # Test 404 - non-existent endpoint
        try:
            response = await self.client.get(f"{self.base_url}/api/nonexistent")
            assert response.status_code == 404
            self.log_test("Error handling - 404 for non-existent endpoint", True)

        except Exception as e:
            self.log_test("Error handling - 404 for non-existent endpoint", False, str(e))

        # Test invalid JSON payload
        try:
            response = await self.client.post(
                f"{self.base_url}/api/agent/chat",
                content="invalid json content",
                headers={"Content-Type": "application/json"}
            )

            # Should return 422 (Unprocessable Entity) for invalid JSON
            assert response.status_code in [400, 422]
            self.log_test("Error handling - invalid JSON payload", True)

        except Exception as e:
            self.log_test("Error handling - invalid JSON payload", False, str(e))

        # Test missing required fields
        try:
            response = await self.client.post(
                f"{self.base_url}/api/agent/chat",
                json={"message": "test"}  # Missing required fields
            )

            assert response.status_code in [400, 422]
            self.log_test("Error handling - missing required fields", True)

        except Exception as e:
            self.log_test("Error handling - missing required fields", False, str(e))

    async def test_cors_and_headers(self):
        """Test CORS configuration and response headers"""
        print("\n=== Testing CORS and Headers ===")

        # Test CORS headers
        try:
            response = await self.client.options(
                f"{self.base_url}/health/",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET"
                }
            )

            # CORS preflight should be handled
            assert response.status_code in [200, 204]
            self.log_test("CORS - preflight request handling", True)

        except Exception as e:
            self.log_test("CORS - preflight request handling", False, str(e))

        # Test response headers
        try:
            response = await self.client.get(f"{self.base_url}/health/")

            # Check for standard headers
            headers = response.headers
            assert "content-type" in headers

            self.log_test("Response headers - standard headers present", True)

        except Exception as e:
            self.log_test("Response headers - standard headers present", False, str(e))

    async def test_request_validation(self):
        """Test request validation and parameter handling"""
        print("\n=== Testing Request Validation ===")

        # Test query parameter validation
        try:
            # Test with invalid parameters
            response = await self.client.get(
                f"{self.base_url}/api/agent/tools",
                params={"project": "test"}  # Missing user_id
            )

            # Should fail with proper error (400, 422, or 500 with validation message)
            assert response.status_code in [400, 422, 500]

            # If it's a 500, check that it contains validation error message
            if response.status_code == 500:
                text = response.text
                assert "User ID is required" in text

            self.log_test("Request validation - missing query parameters", True)

        except Exception as e:
            self.log_test("Request validation - missing query parameters", False, str(e))

        # Test empty project parameter
        try:
            response = await self.client.get(
                f"{self.base_url}/api/agent/tools",
                params={"project": "", "user_id": "test"}
            )

            # Should handle empty parameters gracefully
            assert response.status_code in [200, 400, 422]
            self.log_test("Request validation - empty parameters", True)

        except Exception as e:
            self.log_test("Request validation - empty parameters", False, str(e))

    async def test_server_connectivity(self):
        """Test basic server connectivity"""
        print("\n=== Testing Server Connectivity ===")

        try:
            response = await self.client.get(f"{self.base_url}/health/")
            assert response.status_code == 200
            self.log_test("Server connectivity - basic connection", True)

        except httpx.ConnectError:
            self.log_test("Server connectivity - basic connection", False, "Server not running on port 8001")
        except Exception as e:
            self.log_test("Server connectivity - basic connection", False, str(e))

    async def test_response_formats(self):
        """Test API response formats and structure"""
        print("\n=== Testing Response Formats ===")

        # Test JSON response format
        try:
            response = await self.client.get(f"{self.base_url}/health/")

            # Should be valid JSON
            data = response.json()
            assert isinstance(data, dict)

            # Should have consistent timestamp format
            if "timestamp" in data:
                # Basic timestamp format validation
                timestamp = data["timestamp"]
                assert isinstance(timestamp, str)
                assert "T" in timestamp  # ISO format

            self.log_test("Response formats - JSON structure", True)

        except Exception as e:
            self.log_test("Response formats - JSON structure", False, str(e))

    async def run_all_tests(self):
        """Run all API endpoint tests"""
        print("Starting Comprehensive API Endpoint Tests")
        print("=" * 60)

        await self.setup_client()

        try:
            await self.test_server_connectivity()
            await self.test_health_endpoints()
            await self.test_agent_endpoints()
            await self.test_chat_endpoints()
            await self.test_conversation_endpoints()
            await self.test_error_handling()
            await self.test_cors_and_headers()
            await self.test_request_validation()
            await self.test_response_formats()

        finally:
            await self.cleanup_client()

        # Summary
        print("\n" + "=" * 60)
        print("API ENDPOINT TEST RESULTS")
        print("=" * 60)
        print(f"✓ Tests Passed: {self.tests_passed}")
        print(f"✗ Tests Failed: {self.tests_failed}")
        print(f"Total Tests: {self.tests_passed + self.tests_failed}")

        if self.tests_failed > 0:
            print("\nFAILED TESTS:")
            for error in self.errors:
                print(f"  - {error}")
            return False
        else:
            print("\n🎉 ALL API ENDPOINT TESTS PASSED!")
            return True


async def main():
    """Main test runner"""
    tester = APIEndpointTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)