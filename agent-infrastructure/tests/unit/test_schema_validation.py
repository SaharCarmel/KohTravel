#!/usr/bin/env python3
"""
Comprehensive Schema Validation Test for Phase 2.2
Tests all tool schemas with valid and invalid data to ensure proper validation.
"""

import sys
import json
from datetime import datetime
from typing import Dict, Any, List
from pydantic import ValidationError

# Add src to path for imports
sys.path.append('src')

from schemas.tool_schemas import (
    # Enums
    ToolStatus, ToolHealthStatus, ToolType, SecurityLevel,

    # Core schemas
    ToolParameter, ToolSchema, ToolSecurityPolicy, ToolMetrics,
    ToolRegistrationRequest, ToolUpdateRequest, ToolDefinition,

    # Validation schemas
    ToolValidationRequest, ToolValidationResult, ToolHealthCheckResult,

    # Response schemas
    ToolRegistrationResponse, ToolListResponse, ToolHealthReport,

    # Query schemas
    ToolListQuery,

    # Error schemas
    ToolValidationError, ToolErrorResponse, ToolOperationResponse
)


class SchemaValidator:
    """Comprehensive schema validation test suite"""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []

    def log_test(self, test_name: str, passed: bool, error: str = None):
        """Log test result"""
        if passed:
            self.tests_passed += 1
            print(f"✓ {test_name}")
        else:
            self.tests_failed += 1
            self.errors.append(f"{test_name}: {error}")
            print(f"✗ {test_name}: {error}")

    def test_enums(self):
        """Test all enum values"""
        print("\n=== Testing Enums ===")

        # ToolStatus
        try:
            assert ToolStatus.ACTIVE == "active"
            assert ToolStatus.INACTIVE == "inactive"
            assert ToolStatus.ERROR == "error"
            assert ToolStatus.VALIDATING == "validating"
            assert ToolStatus.MAINTENANCE == "maintenance"
            self.log_test("ToolStatus enum values", True)
        except Exception as e:
            self.log_test("ToolStatus enum values", False, str(e))

        # ToolHealthStatus
        try:
            assert ToolHealthStatus.HEALTHY == "healthy"
            assert ToolHealthStatus.DEGRADED == "degraded"
            assert ToolHealthStatus.UNHEALTHY == "unhealthy"
            assert ToolHealthStatus.UNKNOWN == "unknown"
            assert ToolHealthStatus.UNREACHABLE == "unreachable"
            self.log_test("ToolHealthStatus enum values", True)
        except Exception as e:
            self.log_test("ToolHealthStatus enum values", False, str(e))

    def test_tool_parameter_schema(self):
        """Test ToolParameter schema validation"""
        print("\n=== Testing ToolParameter Schema ===")

        # Valid parameter
        try:
            param = ToolParameter(
                name="search_query",
                type="string",
                description="Search query text",
                required=True,
                pattern=r"^[a-zA-Z0-9\s]+$"
            )
            self.log_test("Valid ToolParameter creation", True)
        except Exception as e:
            self.log_test("Valid ToolParameter creation", False, str(e))

        # Invalid parameter name
        try:
            ToolParameter(
                name="123invalid",  # starts with number
                type="string",
                description="Invalid parameter"
            )
            self.log_test("Invalid parameter name validation", False, "Should have failed")
        except ValidationError:
            self.log_test("Invalid parameter name validation", True)
        except Exception as e:
            self.log_test("Invalid parameter name validation", False, str(e))

    def test_tool_schema(self):
        """Test ToolSchema validation"""
        print("\n=== Testing ToolSchema ===")

        # Valid schema
        try:
            schema = ToolSchema(
                type="object",
                properties={
                    "query": ToolParameter(
                        name="query",
                        type="string",
                        description="Search query",
                        required=True
                    )
                },
                required=["query"],
                description="Search tool input schema"
            )
            self.log_test("Valid ToolSchema creation", True)
        except Exception as e:
            self.log_test("Valid ToolSchema creation", False, str(e))

        # Invalid required fields
        try:
            ToolSchema(
                type="object",
                properties={
                    "query": ToolParameter(
                        name="query",
                        type="string",
                        description="Search query"
                    )
                },
                required=["nonexistent_field"]  # Field not in properties
            )
            self.log_test("Invalid required fields validation", False, "Should have failed")
        except ValidationError:
            self.log_test("Invalid required fields validation", True)
        except Exception as e:
            self.log_test("Invalid required fields validation", False, str(e))

    def test_security_policy(self):
        """Test ToolSecurityPolicy validation"""
        print("\n=== Testing ToolSecurityPolicy ===")

        # Valid security policy
        try:
            policy = ToolSecurityPolicy(
                security_level=SecurityLevel.HIGH,
                allowed_domains=["api.example.com", "secure.example.com"],
                require_https=True,
                timeout_seconds=60,
                rate_limit_per_minute=50
            )
            self.log_test("Valid ToolSecurityPolicy creation", True)
        except Exception as e:
            self.log_test("Valid ToolSecurityPolicy creation", False, str(e))

        # Invalid domain format
        try:
            ToolSecurityPolicy(
                allowed_domains=["invalid-domain"]  # No TLD
            )
            self.log_test("Invalid domain validation", False, "Should have failed")
        except ValidationError:
            self.log_test("Invalid domain validation", True)
        except Exception as e:
            self.log_test("Invalid domain validation", False, str(e))

        # Invalid timeout range
        try:
            ToolSecurityPolicy(
                timeout_seconds=500  # Over 300 limit
            )
            self.log_test("Invalid timeout range validation", False, "Should have failed")
        except ValidationError:
            self.log_test("Invalid timeout range validation", True)
        except Exception as e:
            self.log_test("Invalid timeout range validation", False, str(e))

    def test_tool_registration_request(self):
        """Test ToolRegistrationRequest validation"""
        print("\n=== Testing ToolRegistrationRequest ===")

        # Valid external tool registration
        try:
            request = ToolRegistrationRequest(
                name="document_search",
                type=ToolType.EXTERNAL,
                description="Search user documents",
                endpoint_url="https://api.example.com/search",
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
                security_policy=ToolSecurityPolicy(
                    security_level=SecurityLevel.MEDIUM
                ),
                tags=["search", "documents"],
                version="1.2.0"
            )
            self.log_test("Valid external tool registration", True)
        except Exception as e:
            self.log_test("Valid external tool registration", False, str(e))

        # Invalid tool name
        try:
            ToolRegistrationRequest(
                name="invalid-name-with-too-many-characters-exceeding-limit",
                type=ToolType.INTERNAL,
                description="Invalid tool"
            )
            self.log_test("Invalid tool name length validation", False, "Should have failed")
        except ValidationError:
            self.log_test("Invalid tool name length validation", True)
        except Exception as e:
            self.log_test("Invalid tool name length validation", False, str(e))

        # External tool without endpoint
        try:
            ToolRegistrationRequest(
                name="external_tool",
                type=ToolType.EXTERNAL,
                description="External tool without endpoint"
                # Missing endpoint_url
            )
            self.log_test("External tool missing endpoint validation", False, "Should have failed")
        except ValidationError:
            self.log_test("External tool missing endpoint validation", True)
        except Exception as e:
            self.log_test("External tool missing endpoint validation", False, str(e))

        # Internal tool with endpoint
        try:
            ToolRegistrationRequest(
                name="internal_tool",
                type=ToolType.INTERNAL,
                description="Internal tool with endpoint",
                endpoint_url="https://should-not-have.com"
            )
            self.log_test("Internal tool with endpoint validation", False, "Should have failed")
        except ValidationError:
            self.log_test("Internal tool with endpoint validation", True)
        except Exception as e:
            self.log_test("Internal tool with endpoint validation", False, str(e))

        # Invalid version format
        try:
            ToolRegistrationRequest(
                name="versioned_tool",
                type=ToolType.INTERNAL,
                description="Tool with invalid version",
                version="not.a.version"
            )
            self.log_test("Invalid version format validation", False, "Should have failed")
        except ValidationError:
            self.log_test("Invalid version format validation", True)
        except Exception as e:
            self.log_test("Invalid version format validation", False, str(e))

    def test_tool_definition(self):
        """Test ToolDefinition schema"""
        print("\n=== Testing ToolDefinition ===")

        # Valid tool definition
        try:
            now = datetime.now()
            definition = ToolDefinition(
                id="tool_123",
                agent_id="agent_456",
                name="search_tool",
                type=ToolType.EXTERNAL,
                description="Document search tool",
                endpoint_url="https://api.example.com/search",
                security_policy=ToolSecurityPolicy(),
                status=ToolStatus.ACTIVE,
                health=ToolHealthStatus.HEALTHY,
                enabled=True,
                tags=["search"],
                version="1.0.0",
                metrics=ToolMetrics(
                    total_calls=100,
                    successful_calls=95,
                    failed_calls=5,
                    avg_response_time_ms=250.5,
                    error_rate=5.0
                ),
                created_at=now,
                updated_at=now,
                last_health_check=now
            )
            self.log_test("Valid ToolDefinition creation", True)
        except Exception as e:
            self.log_test("Valid ToolDefinition creation", False, str(e))

    def test_validation_schemas(self):
        """Test validation and health check schemas"""
        print("\n=== Testing Validation Schemas ===")

        # ToolValidationRequest
        try:
            request = ToolValidationRequest(
                validate_connectivity=True,
                validate_schema=True,
                validate_security=True,
                test_call=False
            )
            self.log_test("Valid ToolValidationRequest", True)
        except Exception as e:
            self.log_test("Valid ToolValidationRequest", False, str(e))

        # ToolValidationResult
        try:
            result = ToolValidationResult(
                tool_id="tool_123",
                tool_name="search_tool",
                is_valid=True,
                connectivity_check=True,
                schema_validation=True,
                security_validation=True,
                test_call_success=True,
                response_time_ms=150.0,
                error_details=[],
                warnings=["Minor warning about response format"],
                last_validated_at=datetime.now()
            )
            self.log_test("Valid ToolValidationResult", True)
        except Exception as e:
            self.log_test("Valid ToolValidationResult", False, str(e))

        # ToolHealthCheckResult
        try:
            health_result = ToolHealthCheckResult(
                tool_id="tool_123",
                tool_name="search_tool",
                health_status=ToolHealthStatus.HEALTHY,
                is_reachable=True,
                response_time_ms=120.0,
                status_code=200,
                last_successful_call=datetime.now(),
                uptime_percentage=99.9,
                checked_at=datetime.now()
            )
            self.log_test("Valid ToolHealthCheckResult", True)
        except Exception as e:
            self.log_test("Valid ToolHealthCheckResult", False, str(e))

    def test_query_schemas(self):
        """Test query parameter schemas"""
        print("\n=== Testing Query Schemas ===")

        # Valid query
        try:
            query = ToolListQuery(
                agent_id="agent_123",
                type=ToolType.EXTERNAL,
                status=ToolStatus.ACTIVE,
                health=ToolHealthStatus.HEALTHY,
                tags=["search", "documents"],
                search="document",
                page=2,
                page_size=50,
                sort_by="created_at",
                sort_order="desc"
            )
            self.log_test("Valid ToolListQuery", True)
        except Exception as e:
            self.log_test("Valid ToolListQuery", False, str(e))

        # Invalid sort field
        try:
            ToolListQuery(
                sort_by="invalid_field"
            )
            self.log_test("Invalid sort field validation", False, "Should have failed")
        except ValidationError:
            self.log_test("Invalid sort field validation", True)
        except Exception as e:
            self.log_test("Invalid sort field validation", False, str(e))

        # Invalid sort order
        try:
            ToolListQuery(
                sort_order="invalid"
            )
            self.log_test("Invalid sort order validation", False, "Should have failed")
        except ValidationError:
            self.log_test("Invalid sort order validation", True)
        except Exception as e:
            self.log_test("Invalid sort order validation", False, str(e))

    def test_error_schemas(self):
        """Test error response schemas"""
        print("\n=== Testing Error Schemas ===")

        # ToolValidationError
        try:
            error = ToolValidationError(
                field="endpoint_url",
                message="Invalid URL format",
                value="not-a-url",
                suggestion="Use format: https://domain.com/path"
            )
            self.log_test("Valid ToolValidationError", True)
        except Exception as e:
            self.log_test("Valid ToolValidationError", False, str(e))

        # ToolErrorResponse
        try:
            error_response = ToolErrorResponse(
                error_code="TOOL_VALIDATION_FAILED",
                message="Tool validation failed",
                tool_id="tool_123",
                details=[
                    ToolValidationError(
                        field="endpoint_url",
                        message="Invalid URL",
                        value="bad-url"
                    )
                ],
                correlation_id="req_456"
            )
            self.log_test("Valid ToolErrorResponse", True)
        except Exception as e:
            self.log_test("Valid ToolErrorResponse", False, str(e))

    def test_response_schemas(self):
        """Test response schemas"""
        print("\n=== Testing Response Schemas ===")

        # ToolRegistrationResponse
        try:
            now = datetime.now()
            definition = ToolDefinition(
                id="tool_123",
                agent_id="agent_456",
                name="test_tool",
                type=ToolType.INTERNAL,
                description="Test tool",
                security_policy=ToolSecurityPolicy(),
                created_at=now,
                updated_at=now
            )

            response = ToolRegistrationResponse(
                tool_id="tool_123",
                message="Tool registered successfully",
                tool=definition,
                validation_result=ToolValidationResult(
                    tool_id="tool_123",
                    tool_name="test_tool",
                    is_valid=True,
                    connectivity_check=True,
                    schema_validation=True,
                    security_validation=True,
                    last_validated_at=now
                )
            )
            self.log_test("Valid ToolRegistrationResponse", True)
        except Exception as e:
            self.log_test("Valid ToolRegistrationResponse", False, str(e))

    def run_all_tests(self):
        """Run all schema validation tests"""
        print("Starting Comprehensive Schema Validation Tests")
        print("=" * 60)

        self.test_enums()
        self.test_tool_parameter_schema()
        self.test_tool_schema()
        self.test_security_policy()
        self.test_tool_registration_request()
        self.test_tool_definition()
        self.test_validation_schemas()
        self.test_query_schemas()
        self.test_error_schemas()
        self.test_response_schemas()

        # Summary
        print("\n" + "=" * 60)
        print("SCHEMA VALIDATION TEST RESULTS")
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
            print("\n🎉 ALL SCHEMA VALIDATION TESTS PASSED!")
            return True


if __name__ == "__main__":
    validator = SchemaValidator()
    success = validator.run_all_tests()
    sys.exit(0 if success else 1)