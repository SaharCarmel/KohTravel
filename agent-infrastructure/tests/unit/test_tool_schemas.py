"""
Unit tests for tool schema validation and functionality.

Tests all Pydantic schemas used in the dynamic tool management system,
ensuring proper validation, error handling, and Pydantic v2 compatibility.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.schemas.tool_schemas import (
    ToolParameter, ToolSchema, ToolSecurityPolicy, ToolRegistrationRequest,
    ToolUpdateRequest, ToolDefinition, ToolValidationRequest, ToolValidationResult,
    ToolHealthCheckResult, ToolListQuery, ToolMetrics,
    ToolStatus, ToolHealthStatus, ToolType, SecurityLevel
)


class TestToolParameter:
    """Test ToolParameter schema validation."""

    def test_valid_tool_parameter(self):
        """Test valid tool parameter creation."""
        param = ToolParameter(
            name="test_param",
            type="string",
            description="Test parameter",
            required=True,
            default="default_value"
        )
        assert param.name == "test_param"
        assert param.type == "string"
        assert param.required is True
        assert param.default == "default_value"

    def test_parameter_name_validation(self):
        """Test parameter name validation rules."""
        # Valid names
        valid_names = ["param", "param_name", "param123", "paramName"]
        for name in valid_names:
            param = ToolParameter(name=name, type="string", description="Test")
            assert param.name == name

        # Invalid names
        invalid_names = ["123param", "param-name", "param.name", ""]
        for name in invalid_names:
            with pytest.raises(ValidationError, match="String should match pattern"):
                ToolParameter(name=name, type="string", description="Test")

    def test_optional_fields(self):
        """Test optional parameter fields."""
        param = ToolParameter(
            name="test_param",
            type="number",
            description="Test parameter",
            minimum=0,
            maximum=100,
            enum=[1, 2, 3],
            pattern=r"\d+"
        )
        assert param.minimum == 0
        assert param.maximum == 100
        assert param.enum == [1, 2, 3]
        assert param.pattern == r"\d+"


class TestToolSchema:
    """Test ToolSchema validation and functionality."""

    def test_valid_tool_schema(self):
        """Test valid tool schema creation."""
        schema = ToolSchema(
            type="object",
            properties={
                "param1": ToolParameter(name="param1", type="string", description="Test param")
            },
            required=["param1"],
            description="Test schema"
        )
        assert schema.type == "object"
        assert "param1" in schema.properties
        assert schema.required == ["param1"]

    def test_required_fields_validation(self):
        """Test validation of required fields against properties."""
        # Valid: required field exists in properties
        ToolSchema(
            type="object",
            properties={
                "param1": ToolParameter(name="param1", type="string", description="Test")
            },
            required=["param1"]
        )

        # Invalid: required field not in properties
        with pytest.raises(ValidationError, match="Required fields not found in properties"):
            ToolSchema(
                type="object",
                properties={
                    "param1": ToolParameter(name="param1", type="string", description="Test")
                },
                required=["param2"]  # param2 doesn't exist
            )

    def test_empty_schema(self):
        """Test empty schema creation."""
        schema = ToolSchema(type="object")
        assert schema.type == "object"
        assert schema.properties is None
        assert schema.required is None


class TestToolSecurityPolicy:
    """Test ToolSecurityPolicy validation."""

    def test_default_security_policy(self):
        """Test default security policy values."""
        policy = ToolSecurityPolicy()
        assert policy.security_level == SecurityLevel.MEDIUM
        assert policy.require_https is True
        assert policy.timeout_seconds == 30
        assert policy.rate_limit_per_minute == 100
        assert policy.audit_calls is True

    def test_domain_validation(self):
        """Test domain validation in security policy."""
        # Valid domains (must have TLD format)
        valid_domains = ["example.com", "api.example.com", "test.localhost"]
        policy = ToolSecurityPolicy(allowed_domains=valid_domains)
        assert policy.allowed_domains == valid_domains

        # Invalid domains (localhost without TLD should fail)
        with pytest.raises(ValidationError, match="Invalid domain format"):
            ToolSecurityPolicy(allowed_domains=["localhost"])

    def test_timeout_range_validation(self):
        """Test timeout range validation."""
        # Valid timeouts
        ToolSecurityPolicy(timeout_seconds=1)
        ToolSecurityPolicy(timeout_seconds=300)

        # Invalid timeouts
        with pytest.raises(ValidationError):
            ToolSecurityPolicy(timeout_seconds=0)
        with pytest.raises(ValidationError):
            ToolSecurityPolicy(timeout_seconds=301)

    def test_rate_limit_validation(self):
        """Test rate limit validation."""
        # Valid rate limits
        ToolSecurityPolicy(rate_limit_per_minute=1)
        ToolSecurityPolicy(rate_limit_per_minute=1000)

        # Invalid rate limits
        with pytest.raises(ValidationError):
            ToolSecurityPolicy(rate_limit_per_minute=0)
        with pytest.raises(ValidationError):
            ToolSecurityPolicy(rate_limit_per_minute=1001)


class TestToolRegistrationRequest:
    """Test ToolRegistrationRequest validation."""

    def test_valid_registration_request(self):
        """Test valid tool registration request."""
        request = ToolRegistrationRequest(
            name="test_tool",
            type=ToolType.EXTERNAL,
            description="Test tool description",
            endpoint_url="https://api.example.com/tool",
            enabled=True,
            tags=["test", "external"],
            version="1.0.0"
        )
        assert request.name == "test_tool"
        assert request.type == ToolType.EXTERNAL
        assert request.endpoint_url == "https://api.example.com/tool"

    def test_tool_name_validation(self):
        """Test tool name validation rules."""
        # Valid names
        valid_names = ["tool", "tool_name", "tool-name", "tool123"]
        for name in valid_names:
            request = ToolRegistrationRequest(
                name=name,
                type=ToolType.EXTERNAL,
                description="Test",
                endpoint_url="https://api.example.com"
            )
            assert request.name == name

        # Invalid names
        with pytest.raises(ValidationError, match="String should match pattern"):
            ToolRegistrationRequest(
                name="123tool",
                type=ToolType.EXTERNAL,
                description="Test",
                endpoint_url="https://api.example.com"
            )

        # Name too long
        with pytest.raises(ValidationError, match="String should have at most"):
            ToolRegistrationRequest(
                name="a" * 51,
                type=ToolType.EXTERNAL,
                description="Test",
                endpoint_url="https://api.example.com"
            )

    def test_endpoint_url_validation(self):
        """Test endpoint URL validation for different tool types."""
        # External tool must have endpoint URL
        ToolRegistrationRequest(
            name="external_tool",
            type=ToolType.EXTERNAL,
            description="Test",
            endpoint_url="https://api.example.com"
        )

        # External tool without endpoint URL should fail
        with pytest.raises(ValidationError, match="External tools must have an endpoint URL"):
            ToolRegistrationRequest(
                name="external_tool",
                type=ToolType.EXTERNAL,
                description="Test"
            )

        # Internal tool should not have endpoint URL
        with pytest.raises(ValidationError, match="internal tools should not have endpoint URLs"):
            ToolRegistrationRequest(
                name="internal_tool",
                type=ToolType.INTERNAL,
                description="Test",
                endpoint_url="https://api.example.com"
            )

        # Invalid URL format
        with pytest.raises(ValidationError, match="Endpoint URL must start with http"):
            ToolRegistrationRequest(
                name="tool",
                type=ToolType.EXTERNAL,
                description="Test",
                endpoint_url="ftp://example.com"
            )

    def test_version_validation(self):
        """Test semantic version validation."""
        # Valid versions
        valid_versions = ["1.0.0", "2.1.3", "1.0.0-beta", "1.2.3-alpha.1"]
        for version in valid_versions:
            request = ToolRegistrationRequest(
                name="tool",
                type=ToolType.INTERNAL,
                description="Test",
                version=version
            )
            assert request.version == version

        # Invalid versions
        invalid_versions = ["1.0", "v1.0.0", "1.0.0.0", "invalid"]
        for version in invalid_versions:
            with pytest.raises(ValidationError, match="String should match pattern"):
                ToolRegistrationRequest(
                    name="tool",
                    type=ToolType.INTERNAL,
                    description="Test",
                    version=version
                )


class TestToolDefinition:
    """Test ToolDefinition schema."""

    def test_valid_tool_definition(self):
        """Test valid tool definition creation."""
        definition = ToolDefinition(
            id="tool_123",
            agent_id="agent_456",
            name="test_tool",
            type=ToolType.EXTERNAL,
            description="Test tool",
            endpoint_url="https://api.example.com",
            security_policy=ToolSecurityPolicy(),
            status=ToolStatus.ACTIVE,
            health=ToolHealthStatus.HEALTHY,
            enabled=True,
            tags=["test"],
            version="1.0.0",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert definition.id == "tool_123"
        assert definition.agent_id == "agent_456"
        assert definition.status == ToolStatus.ACTIVE
        assert definition.health == ToolHealthStatus.HEALTHY

    def test_model_config(self):
        """Test model configuration for ORM compatibility."""
        # Test that from_attributes is properly configured
        assert hasattr(ToolDefinition, "model_config")
        assert ToolDefinition.model_config["from_attributes"] is True


class TestToolValidationResult:
    """Test ToolValidationResult schema."""

    def test_validation_result_creation(self):
        """Test validation result creation."""
        result = ToolValidationResult(
            tool_id="tool_123",
            tool_name="test_tool",
            is_valid=True,
            connectivity_check=True,
            schema_validation=True,
            security_validation=True,
            response_time_ms=150.5,
            last_validated_at=datetime.now(timezone.utc)
        )
        assert result.is_valid is True
        assert result.connectivity_check is True
        assert result.response_time_ms == 150.5

    def test_validation_result_with_errors(self):
        """Test validation result with error details."""
        result = ToolValidationResult(
            tool_id="tool_123",
            tool_name="test_tool",
            is_valid=False,
            connectivity_check=False,
            schema_validation=True,
            security_validation=False,
            error_details=["Connection timeout", "Invalid security policy"],
            warnings=["Deprecated endpoint"],
            last_validated_at=datetime.now(timezone.utc)
        )
        assert result.is_valid is False
        assert len(result.error_details) == 2
        assert len(result.warnings) == 1


class TestToolHealthCheckResult:
    """Test ToolHealthCheckResult schema."""

    def test_health_check_result(self):
        """Test health check result creation."""
        result = ToolHealthCheckResult(
            tool_id="tool_123",
            tool_name="test_tool",
            health_status=ToolHealthStatus.HEALTHY,
            is_reachable=True,
            response_time_ms=50.0,
            status_code=200,
            uptime_percentage=99.9,
            checked_at=datetime.now(timezone.utc)
        )
        assert result.health_status == ToolHealthStatus.HEALTHY
        assert result.is_reachable is True
        assert result.uptime_percentage == 99.9

    def test_unhealthy_check_result(self):
        """Test unhealthy health check result."""
        result = ToolHealthCheckResult(
            tool_id="tool_123",
            tool_name="test_tool",
            health_status=ToolHealthStatus.UNHEALTHY,
            is_reachable=False,
            error_message="Connection refused",
            uptime_percentage=85.5,
            checked_at=datetime.now(timezone.utc)
        )
        assert result.health_status == ToolHealthStatus.UNHEALTHY
        assert result.is_reachable is False
        assert result.error_message == "Connection refused"


class TestToolListQuery:
    """Test ToolListQuery validation."""

    def test_default_query_parameters(self):
        """Test default query parameter values."""
        query = ToolListQuery()
        assert query.page == 1
        assert query.page_size == 20
        assert query.sort_by == "created_at"
        assert query.sort_order == "desc"

    def test_sort_field_validation(self):
        """Test sort field validation."""
        # Valid sort fields
        valid_fields = ["created_at", "updated_at", "name", "type", "status", "health"]
        for field in valid_fields:
            query = ToolListQuery(sort_by=field)
            assert query.sort_by == field

        # Invalid sort field
        with pytest.raises(ValidationError, match="String should match pattern"):
            ToolListQuery(sort_by="invalid_field")

    def test_sort_order_validation(self):
        """Test sort order validation."""
        # Valid sort orders
        query_asc = ToolListQuery(sort_order="asc")
        query_desc = ToolListQuery(sort_order="desc")
        assert query_asc.sort_order == "asc"
        assert query_desc.sort_order == "desc"

        # Invalid sort order
        with pytest.raises(ValidationError, match="String should match pattern"):
            ToolListQuery(sort_order="invalid")

    def test_page_validation(self):
        """Test page number validation."""
        # Valid page numbers
        ToolListQuery(page=1)
        ToolListQuery(page=100)

        # Invalid page numbers
        with pytest.raises(ValidationError):
            ToolListQuery(page=0)

    def test_page_size_validation(self):
        """Test page size validation."""
        # Valid page sizes
        ToolListQuery(page_size=1)
        ToolListQuery(page_size=100)

        # Invalid page sizes
        with pytest.raises(ValidationError):
            ToolListQuery(page_size=0)
        with pytest.raises(ValidationError):
            ToolListQuery(page_size=101)


class TestToolMetrics:
    """Test ToolMetrics schema."""

    def test_default_metrics(self):
        """Test default metric values."""
        metrics = ToolMetrics()
        assert metrics.total_calls == 0
        assert metrics.successful_calls == 0
        assert metrics.failed_calls == 0
        assert metrics.error_rate == 0.0
        assert metrics.availability_percentage == 100.0

    def test_metrics_with_data(self):
        """Test metrics with actual data."""
        metrics = ToolMetrics(
            total_calls=100,
            successful_calls=95,
            failed_calls=5,
            avg_response_time_ms=150.5,
            last_called_at=datetime.now(timezone.utc),
            error_rate=5.0,
            availability_percentage=98.5
        )
        assert metrics.total_calls == 100
        assert metrics.successful_calls == 95
        assert metrics.failed_calls == 5
        assert metrics.error_rate == 5.0


class TestEnumValues:
    """Test enum value consistency."""

    def test_tool_status_values(self):
        """Test ToolStatus enum values."""
        assert ToolStatus.ACTIVE == "active"
        assert ToolStatus.INACTIVE == "inactive"
        assert ToolStatus.ERROR == "error"
        assert ToolStatus.MAINTENANCE == "maintenance"

    def test_tool_health_status_values(self):
        """Test ToolHealthStatus enum values."""
        assert ToolHealthStatus.HEALTHY == "healthy"
        assert ToolHealthStatus.DEGRADED == "degraded"
        assert ToolHealthStatus.UNHEALTHY == "unhealthy"
        assert ToolHealthStatus.UNKNOWN == "unknown"
        assert ToolHealthStatus.UNREACHABLE == "unreachable"

    def test_tool_type_values(self):
        """Test ToolType enum values."""
        assert ToolType.INTERNAL == "internal"
        assert ToolType.EXTERNAL == "external"
        assert ToolType.BUILTIN == "builtin"
        assert ToolType.CUSTOM == "custom"

    def test_security_level_values(self):
        """Test SecurityLevel enum values."""
        assert SecurityLevel.LOW == "low"
        assert SecurityLevel.MEDIUM == "medium"
        assert SecurityLevel.HIGH == "high"
        assert SecurityLevel.CRITICAL == "critical"