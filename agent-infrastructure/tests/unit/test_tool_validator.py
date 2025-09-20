"""
Unit tests for tool validation functionality.

Tests the tool validator including connectivity checks, schema validation,
security validation, and error handling.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.core.tool_registry import ToolValidator
from src.schemas.tool_schemas import (
    ToolRegistrationRequest, ToolValidationResult,
    ToolType, SecurityLevel, ToolSecurityPolicy,
    ToolSchema, ToolParameter
)


class TestToolValidator:
    """Test tool validation functionality."""

    @pytest.fixture
    async def validator(self):
        """Create and cleanup tool validator."""
        validator = ToolValidator()
        yield validator
        await validator.close()

    @pytest.mark.asyncio
    async def test_validator_initialization(self, validator):
        """Test validator initialization."""
        assert validator is not None
        assert hasattr(validator, 'client')

    @pytest.mark.asyncio
    async def test_validate_external_tool_with_valid_connectivity(self, validator):
        """Test validation of external tool with successful connectivity."""
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

        # Mock successful connectivity check
        with patch.object(validator, '_check_connectivity', return_value=True):
            result = await validator.validate_tool_registration(tool_request)

            assert isinstance(result, ToolValidationResult)
            assert result.tool_name == "test_external_tool"
            assert result.is_valid is True
            assert result.schema_validation is True
            assert result.security_validation is True
            assert result.connectivity_check is True
            assert result.error_details is None or len(result.error_details) == 0

    @pytest.mark.asyncio
    async def test_validate_external_tool_with_failed_connectivity(self, validator):
        """Test validation of external tool with failed connectivity."""
        tool_request = ToolRegistrationRequest(
            name="test_unreachable_tool",
            type=ToolType.EXTERNAL,
            description="Test unreachable tool",
            endpoint_url="https://unreachable-domain-12345.com/tools"
        )

        # Mock failed connectivity check
        with patch.object(validator, '_check_connectivity', return_value=False):
            result = await validator.validate_tool_registration(tool_request)

            assert result.schema_validation is True
            assert result.security_validation is True
            assert result.connectivity_check is False
            assert result.is_valid is False

    @pytest.mark.asyncio
    async def test_validate_internal_tool(self, validator):
        """Test validation of internal tool (no connectivity check needed)."""
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

        assert result.is_valid is True
        assert result.schema_validation is True
        assert result.security_validation is True
        assert result.connectivity_check is True  # Internal tools don't need connectivity

    @pytest.mark.asyncio
    async def test_validate_builtin_tool(self, validator):
        """Test validation of builtin tool."""
        tool_request = ToolRegistrationRequest(
            name="test_builtin_tool",
            type=ToolType.BUILTIN,
            description="Test builtin tool"
        )

        result = await validator.validate_tool_registration(tool_request)

        assert result.is_valid is True
        assert result.schema_validation is True
        assert result.security_validation is True
        assert result.connectivity_check is True

    @pytest.mark.asyncio
    async def test_validate_tool_with_high_security_level(self, validator):
        """Test validation of tool with high security requirements."""
        tool_request = ToolRegistrationRequest(
            name="test_secure_tool",
            type=ToolType.EXTERNAL,
            description="Test secure tool",
            endpoint_url="https://secure-api.example.com/tools",
            security_policy=ToolSecurityPolicy(
                security_level=SecurityLevel.HIGH,
                require_https=True,
                timeout_seconds=10,
                rate_limit_per_minute=10,
                allowed_domains=["secure-api.example.com"]
            )
        )

        with patch.object(validator, '_check_connectivity', return_value=True):
            result = await validator.validate_tool_registration(tool_request)

            assert result.security_validation is True
            assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_validate_tool_with_invalid_https_requirement(self, validator):
        """Test validation failure for HTTP endpoint when HTTPS required."""
        tool_request = ToolRegistrationRequest(
            name="test_insecure_tool",
            type=ToolType.EXTERNAL,
            description="Test insecure tool",
            endpoint_url="http://insecure-api.example.com/tools",  # HTTP not HTTPS
            security_policy=ToolSecurityPolicy(
                security_level=SecurityLevel.HIGH,
                require_https=True
            )
        )

        result = await validator.validate_tool_registration(tool_request)

        assert result.security_validation is False
        assert result.is_valid is False
        assert any("HTTPS required" in error for error in (result.error_details or []))

    @pytest.mark.asyncio
    async def test_validate_tool_with_domain_restriction_violation(self, validator):
        """Test validation failure for domain restriction violation."""
        tool_request = ToolRegistrationRequest(
            name="test_restricted_tool",
            type=ToolType.EXTERNAL,
            description="Test tool with domain restriction",
            endpoint_url="https://forbidden-domain.com/tools",
            security_policy=ToolSecurityPolicy(
                allowed_domains=["allowed-domain.com", "another-allowed.com"]
            )
        )

        result = await validator.validate_tool_registration(tool_request)

        assert result.security_validation is False
        assert result.is_valid is False
        assert any("domain not allowed" in error.lower() for error in (result.error_details or []))

    @pytest.mark.asyncio
    async def test_connectivity_check_timeout(self, validator):
        """Test connectivity check with timeout."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timed out")

            result = await validator._check_connectivity("https://slow-api.example.com")

            assert result is False

    @pytest.mark.asyncio
    async def test_connectivity_check_http_error(self, validator):
        """Test connectivity check with HTTP error."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            result = await validator._check_connectivity("https://api.example.com")

            assert result is False

    @pytest.mark.asyncio
    async def test_connectivity_check_success(self, validator):
        """Test successful connectivity check."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = await validator._check_connectivity("https://api.example.com")

            assert result is True

    @pytest.mark.asyncio
    async def test_security_validation_with_critical_level(self, validator):
        """Test security validation with critical security level."""
        tool_request = ToolRegistrationRequest(
            name="test_critical_tool",
            type=ToolType.EXTERNAL,
            description="Test critical security tool",
            endpoint_url="https://critical-api.example.com/tools",
            security_policy=ToolSecurityPolicy(
                security_level=SecurityLevel.CRITICAL,
                require_https=True,
                timeout_seconds=5,  # Very strict timeout
                rate_limit_per_minute=1,  # Very low rate limit
                audit_calls=True
            )
        )

        with patch.object(validator, '_check_connectivity', return_value=True):
            result = await validator.validate_tool_registration(tool_request)

            assert result.security_validation is True

    @pytest.mark.asyncio
    async def test_schema_validation_with_complex_input_schema(self, validator):
        """Test schema validation with complex input schema."""
        tool_request = ToolRegistrationRequest(
            name="test_complex_schema_tool",
            type=ToolType.INTERNAL,
            description="Test tool with complex schema",
            input_schema=ToolSchema(
                type="object",
                properties={
                    "query": ToolParameter(
                        name="query",
                        type="string",
                        description="Search query",
                        pattern=r"^[a-zA-Z0-9\s]+$"
                    ),
                    "limit": ToolParameter(
                        name="limit",
                        type="number",
                        description="Result limit",
                        minimum=1,
                        maximum=100
                    ),
                    "filters": ToolParameter(
                        name="filters",
                        type="array",
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
                    ),
                    "total": ToolParameter(
                        name="total",
                        type="number",
                        description="Total count"
                    )
                }
            )
        )

        result = await validator.validate_tool_registration(tool_request)

        assert result.schema_validation is True
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_validation_result_timing(self, validator):
        """Test that validation result includes timing information."""
        tool_request = ToolRegistrationRequest(
            name="test_timing_tool",
            type=ToolType.INTERNAL,
            description="Test tool for timing validation"
        )

        result = await validator.validate_tool_registration(tool_request)

        assert result.response_time_ms is not None
        assert result.response_time_ms >= 0
        assert result.last_validated_at is not None

    @pytest.mark.asyncio
    async def test_validator_close_cleanup(self, validator):
        """Test validator cleanup on close."""
        # Validator should be initialized
        assert validator.client is not None

        await validator.close()

        # Client should be closed (note: httpx client might still be accessible
        # but close() should have been called)
        # We can't easily test if client is closed without implementation details

    @pytest.mark.asyncio
    async def test_concurrent_validations(self, validator):
        """Test multiple concurrent validations."""
        tool_requests = []
        for i in range(5):
            tool_requests.append(ToolRegistrationRequest(
                name=f"test_concurrent_tool_{i}",
                type=ToolType.INTERNAL,
                description=f"Test concurrent tool {i}"
            ))

        # Run validations concurrently
        tasks = [validator.validate_tool_registration(req) for req in tool_requests]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 5
        for result in results:
            assert result.is_valid is True
            assert result.schema_validation is True