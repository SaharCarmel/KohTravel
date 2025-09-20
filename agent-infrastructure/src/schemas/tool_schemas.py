"""
Tool Management Schemas for Dynamic Tool System

This module provides comprehensive schemas for the dynamic tool management system,
enabling runtime tool registration, health monitoring, and security validation.

Key Features:
- Dynamic tool registration and deregistration
- Tool health monitoring and validation
- Security policy enforcement
- Performance metrics tracking
- Enhanced error handling with specific tool validation messages
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
import re


class ToolStatus(str, Enum):
    """Tool operational status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    VALIDATING = "validating"
    MAINTENANCE = "maintenance"


class ToolHealthStatus(str, Enum):
    """Tool health monitoring status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    UNREACHABLE = "unreachable"


class ToolType(str, Enum):
    """Tool type classification"""
    INTERNAL = "internal"
    EXTERNAL = "external"
    BUILTIN = "builtin"
    CUSTOM = "custom"


class SecurityLevel(str, Enum):
    """Tool security validation level"""
    LOW = "low"           # Basic validation only
    MEDIUM = "medium"     # Standard validation + endpoint checks
    HIGH = "high"         # Full validation + security audit
    CRITICAL = "critical" # Maximum validation + approval required


# Enhanced Tool Schema Definitions

class ToolParameter(BaseModel):
    """Individual tool parameter definition"""
    name: str = Field(..., description="Parameter name", pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$')
    type: str = Field(..., description="Parameter type (string, number, boolean, object, array)")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Optional[Any] = Field(default=None, description="Default value")
    enum: Optional[List[Any]] = Field(default=None, description="Allowed values if enumerated")
    pattern: Optional[str] = Field(default=None, description="Regex pattern for string validation")
    minimum: Optional[float] = Field(default=None, description="Minimum value for numbers")
    maximum: Optional[float] = Field(default=None, description="Maximum value for numbers")


class ToolSchema(BaseModel):
    """Enhanced tool input/output schema definition"""
    type: str = Field(..., description="Schema type (object, string, etc.)")
    properties: Optional[Dict[str, ToolParameter]] = Field(default=None, description="Schema properties")
    required: Optional[List[str]] = Field(default=None, description="Required fields")
    description: Optional[str] = Field(default=None, description="Schema description")
    additionalProperties: bool = Field(default=False, description="Allow additional properties")

    @model_validator(mode='after')
    def validate_required_fields(self):
        """Validate required fields exist in properties"""
        if self.required and self.properties:
            invalid_fields = [field for field in self.required if field not in self.properties]
            if invalid_fields:
                raise ValueError(f'Required fields not found in properties: {", ".join(invalid_fields)}')
        return self


class ToolSecurityPolicy(BaseModel):
    """Tool security policy configuration"""
    security_level: SecurityLevel = Field(default=SecurityLevel.MEDIUM, description="Security validation level")
    allowed_domains: Optional[List[str]] = Field(default=None, description="Allowed endpoint domains")
    blocked_domains: Optional[List[str]] = Field(default=None, description="Blocked endpoint domains")
    require_https: bool = Field(default=True, description="Require HTTPS for external endpoints")
    max_request_size: int = Field(default=1048576, description="Maximum request size in bytes (1MB default)")
    max_response_size: int = Field(default=10485760, description="Maximum response size in bytes (10MB default)")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Request timeout (1-300 seconds)")
    rate_limit_per_minute: int = Field(default=100, ge=1, le=1000, description="Rate limit per minute")
    require_auth: bool = Field(default=False, description="Whether tool requires authentication")
    audit_calls: bool = Field(default=True, description="Whether to audit tool calls")

    @field_validator('allowed_domains', 'blocked_domains')
    @classmethod
    def validate_domains(cls, v):
        """Validate domain format"""
        if v:
            for domain in v:
                if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain):
                    raise ValueError(f'Invalid domain format: {domain}')
        return v


class ToolMetrics(BaseModel):
    """Tool performance and usage metrics"""
    total_calls: int = Field(default=0, description="Total number of calls")
    successful_calls: int = Field(default=0, description="Number of successful calls")
    failed_calls: int = Field(default=0, description="Number of failed calls")
    avg_response_time_ms: Optional[float] = Field(default=None, description="Average response time")
    last_called_at: Optional[datetime] = Field(default=None, description="Last call timestamp")
    error_rate: float = Field(default=0.0, description="Error rate percentage")
    availability_percentage: float = Field(default=100.0, description="Availability percentage")


# Core Tool Configuration Schemas

class ToolRegistrationRequest(BaseModel):
    """Request schema for registering a new tool"""
    name: str = Field(..., description="Tool name (must be unique within agent)", pattern=r'^[a-zA-Z][a-zA-Z0-9_-]*$', max_length=50)
    type: ToolType = Field(..., description="Tool type classification")
    description: str = Field(..., description="Tool description for agent understanding")
    endpoint_url: Optional[str] = Field(default=None, description="External tool endpoint URL")
    input_schema: Optional[ToolSchema] = Field(default=None, description="Input validation schema")
    output_schema: Optional[ToolSchema] = Field(default=None, description="Output validation schema")
    security_policy: Optional[ToolSecurityPolicy] = Field(default_factory=ToolSecurityPolicy, description="Security configuration")
    enabled: bool = Field(default=True, description="Whether tool is enabled")
    tags: Optional[List[str]] = Field(default=[], description="Tool tags for categorization")
    version: str = Field(default="1.0.0", description="Tool version", pattern=r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?$')

    @model_validator(mode='after')
    def validate_endpoint_url(self):
        """Validate endpoint URL for external tools"""
        if self.type == ToolType.EXTERNAL:
            if not self.endpoint_url:
                raise ValueError('External tools must have an endpoint URL')
            if not (self.endpoint_url.startswith('http://') or self.endpoint_url.startswith('https://')):
                raise ValueError('Endpoint URL must start with http:// or https://')
        elif self.type in [ToolType.INTERNAL, ToolType.BUILTIN] and self.endpoint_url:
            raise ValueError(f'{self.type.value} tools should not have endpoint URLs')
        return self



class ToolUpdateRequest(BaseModel):
    """Request schema for updating tool configuration"""
    description: Optional[str] = Field(default=None, description="Updated tool description")
    endpoint_url: Optional[str] = Field(default=None, description="Updated endpoint URL")
    input_schema: Optional[ToolSchema] = Field(default=None, description="Updated input schema")
    output_schema: Optional[ToolSchema] = Field(default=None, description="Updated output schema")
    security_policy: Optional[ToolSecurityPolicy] = Field(default=None, description="Updated security policy")
    enabled: Optional[bool] = Field(default=None, description="Updated enabled status")
    tags: Optional[List[str]] = Field(default=None, description="Updated tags")
    version: Optional[str] = Field(default=None, description="Updated version", pattern=r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?$')

    @field_validator('endpoint_url')
    @classmethod
    def validate_endpoint_url(cls, v):
        """Validate endpoint URL if provided"""
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('Endpoint URL must start with http:// or https://')
        return v


class ToolDefinition(BaseModel):
    """Complete tool definition with enhanced validation and monitoring"""
    id: str = Field(..., description="Unique tool identifier")
    agent_id: str = Field(..., description="Agent that owns this tool")
    name: str = Field(..., description="Tool name")
    type: ToolType = Field(..., description="Tool type classification")
    description: str = Field(..., description="Tool description")
    endpoint_url: Optional[str] = Field(default=None, description="External tool endpoint URL")
    input_schema: Optional[ToolSchema] = Field(default=None, description="Input validation schema")
    output_schema: Optional[ToolSchema] = Field(default=None, description="Output validation schema")
    security_policy: ToolSecurityPolicy = Field(..., description="Security configuration")
    status: ToolStatus = Field(default=ToolStatus.ACTIVE, description="Tool operational status")
    health: ToolHealthStatus = Field(default=ToolHealthStatus.UNKNOWN, description="Tool health status")
    enabled: bool = Field(default=True, description="Whether tool is enabled")
    tags: List[str] = Field(default=[], description="Tool tags")
    version: str = Field(default="1.0.0", description="Tool version", pattern=r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?$')
    metrics: Optional[ToolMetrics] = Field(default=None, description="Tool performance metrics")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_health_check: Optional[datetime] = Field(default=None, description="Last health check timestamp")

    model_config = {"from_attributes": True}


# Tool Validation and Health Schemas

class ToolValidationRequest(BaseModel):
    """Request schema for tool validation"""
    validate_connectivity: bool = Field(default=True, description="Check endpoint connectivity")
    validate_schema: bool = Field(default=True, description="Validate input/output schemas")
    validate_security: bool = Field(default=True, description="Perform security validation")
    test_call: bool = Field(default=False, description="Perform test call to endpoint")


class ToolValidationResult(BaseModel):
    """Tool validation result with detailed feedback"""
    tool_id: str = Field(..., description="Tool identifier")
    tool_name: str = Field(..., description="Tool name")
    is_valid: bool = Field(..., description="Overall validation status")
    connectivity_check: bool = Field(..., description="Endpoint connectivity status")
    schema_validation: bool = Field(..., description="Schema validation status")
    security_validation: bool = Field(..., description="Security validation status")
    test_call_success: Optional[bool] = Field(default=None, description="Test call result")
    response_time_ms: Optional[float] = Field(default=None, description="Response time in milliseconds")
    error_details: Optional[List[str]] = Field(default=None, description="Validation error details")
    warnings: Optional[List[str]] = Field(default=None, description="Validation warnings")
    last_validated_at: datetime = Field(..., description="Validation timestamp")


class ToolHealthCheckResult(BaseModel):
    """Tool health check result"""
    tool_id: str = Field(..., description="Tool identifier")
    tool_name: str = Field(..., description="Tool name")
    health_status: ToolHealthStatus = Field(..., description="Current health status")
    is_reachable: bool = Field(..., description="Whether tool endpoint is reachable")
    response_time_ms: Optional[float] = Field(default=None, description="Response time")
    status_code: Optional[int] = Field(default=None, description="HTTP status code")
    error_message: Optional[str] = Field(default=None, description="Error details if unhealthy")
    last_successful_call: Optional[datetime] = Field(default=None, description="Last successful call")
    uptime_percentage: float = Field(default=100.0, description="Uptime percentage over last 24h")
    checked_at: datetime = Field(..., description="Health check timestamp")


# Response Schemas

class ToolRegistrationResponse(BaseModel):
    """Response for successful tool registration"""
    tool_id: str = Field(..., description="Created tool identifier")
    message: str = Field(..., description="Success message")
    tool: ToolDefinition = Field(..., description="Created tool details")
    validation_result: Optional[ToolValidationResult] = Field(default=None, description="Initial validation result")


class ToolListResponse(BaseModel):
    """Response for listing tools with pagination"""
    tools: List[ToolDefinition] = Field(..., description="List of tools")
    total: int = Field(..., description="Total number of tools")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


class ToolHealthReport(BaseModel):
    """Comprehensive tool health report"""
    agent_id: str = Field(..., description="Agent identifier")
    total_tools: int = Field(..., description="Total number of tools")
    healthy_tools: int = Field(..., description="Number of healthy tools")
    degraded_tools: int = Field(..., description="Number of degraded tools")
    unhealthy_tools: int = Field(..., description="Number of unhealthy tools")
    unreachable_tools: int = Field(..., description="Number of unreachable tools")
    tool_results: List[ToolHealthCheckResult] = Field(..., description="Individual tool health results")
    overall_health: ToolHealthStatus = Field(..., description="Overall tool health status")
    last_checked_at: datetime = Field(..., description="Health check timestamp")


# Query Parameter Schemas

class ToolListQuery(BaseModel):
    """Query parameters for listing tools"""
    agent_id: Optional[str] = Field(default=None, description="Filter by agent ID")
    type: Optional[ToolType] = Field(default=None, description="Filter by tool type")
    status: Optional[ToolStatus] = Field(default=None, description="Filter by tool status")
    health: Optional[ToolHealthStatus] = Field(default=None, description="Filter by health status")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    search: Optional[str] = Field(default=None, description="Search in name and description")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: str = Field(default="created_at", description="Sort field", pattern=r'^(created_at|updated_at|name|type|status|health|last_called_at)$')
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)", pattern=r'^(asc|desc)$')



# Error Response Schemas

class ToolValidationError(BaseModel):
    """Tool validation error details"""
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Validation error message")
    value: Any = Field(..., description="Invalid value")
    suggestion: Optional[str] = Field(default=None, description="Suggested fix")


class ToolErrorResponse(BaseModel):
    """Tool-specific error response"""
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    tool_id: Optional[str] = Field(default=None, description="Tool identifier if applicable")
    details: Optional[Union[str, List[ToolValidationError]]] = Field(default=None, description="Additional error details")
    correlation_id: Optional[str] = Field(default=None, description="Request correlation ID for tracing")


# Success Response Schemas

class ToolOperationResponse(BaseModel):
    """Generic tool operation response"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation result message")
    tool_id: Optional[str] = Field(default=None, description="Tool identifier if applicable")
    correlation_id: Optional[str] = Field(default=None, description="Request correlation ID")