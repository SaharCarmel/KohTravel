"""
Agent Management API Schemas

This module defines comprehensive Pydantic schemas for the Agent Management System,
following the tech lead's recommendations for enhanced schemas with operational fields.

Key Features:
- Complete agent lifecycle schemas (create, update, response)
- Tool configuration validation with security checks
- Version tracking and health status monitoring
- Enhanced error handling with clear validation messages
- Backward compatibility with Phase 1 database models
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, validator, root_validator
import re


class AgentStatus(str, Enum):
    """Agent operational status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class HealthStatus(str, Enum):
    """Agent health monitoring status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ToolType(str, Enum):
    """Tool type classification"""
    INTERNAL = "internal"
    EXTERNAL = "external"
    BUILTIN = "builtin"


# Tool Configuration Schemas

class ToolSchema(BaseModel):
    """Tool input/output schema definition"""
    type: str = Field(..., description="Schema type (object, string, etc.)")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="Schema properties")
    required: Optional[List[str]] = Field(default=None, description="Required fields")
    description: Optional[str] = Field(default=None, description="Schema description")


class ToolDefinition(BaseModel):
    """Complete tool definition with validation"""
    name: str = Field(..., description="Tool name (must be unique per agent)")
    type: ToolType = Field(..., description="Tool type classification")
    description: str = Field(..., description="Tool description for agent understanding")
    endpoint_url: Optional[str] = Field(default=None, description="External tool endpoint URL")
    input_schema: Optional[ToolSchema] = Field(default=None, description="Input validation schema")
    output_schema: Optional[ToolSchema] = Field(default=None, description="Output validation schema")
    timeout_seconds: int = Field(default=30, description="Tool execution timeout")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    enabled: bool = Field(default=True, description="Whether tool is enabled")

    @validator('name')
    def validate_tool_name(cls, v):
        """Validate tool name format"""
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', v):
            raise ValueError('Tool name must start with letter and contain only letters, numbers, hyphens, and underscores')
        return v

    @validator('endpoint_url')
    def validate_endpoint_url(cls, v, values):
        """Validate endpoint URL for external tools"""
        if values.get('type') == ToolType.EXTERNAL and not v:
            raise ValueError('External tools must have an endpoint URL')
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('Endpoint URL must start with http:// or https://')
        return v


class ModelConfiguration(BaseModel):
    """AI model configuration"""
    model: str = Field(default="claude-3-5-sonnet-20241022", description="LLM model identifier")
    max_tokens: int = Field(default=4096, ge=1, le=200000, description="Maximum tokens for responses")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="Model temperature setting")

    @validator('model')
    def validate_model(cls, v):
        """Validate model identifier"""
        supported_models = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229"
        ]
        if v not in supported_models:
            raise ValueError(f'Model must be one of: {", ".join(supported_models)}')
        return v


# Agent Management Schemas

class AgentCreateRequest(BaseModel):
    """Request schema for creating a new agent"""
    app_name: str = Field(..., description="Application name that owns this agent")
    name: str = Field(..., description="Human-readable agent name")
    description: Optional[str] = Field(default=None, description="Agent description")
    base_system_prompt: str = Field(..., description="Base system prompt for the agent")
    tools: Optional[List[ToolDefinition]] = Field(default=[], description="Agent tool definitions")
    model_configuration: Optional[ModelConfiguration] = Field(default_factory=lambda: ModelConfiguration(), description="Model configuration")

    @validator('app_name')
    def validate_app_name(cls, v):
        """Validate application name format"""
        if not re.match(r'^[a-z][a-z0-9-]*$', v):
            raise ValueError('App name must start with lowercase letter and contain only lowercase letters, numbers, and hyphens')
        return v

    @validator('name')
    def validate_agent_name(cls, v):
        """Validate agent name format"""
        if len(v.strip()) < 2:
            raise ValueError('Agent name must be at least 2 characters long')
        return v.strip()

    @validator('base_system_prompt')
    def validate_system_prompt(cls, v):
        """Validate system prompt"""
        if len(v.strip()) < 10:
            raise ValueError('System prompt must be at least 10 characters long')
        return v.strip()

    @validator('tools')
    def validate_tools(cls, v):
        """Validate tool definitions"""
        if not v:
            return v

        # Check for duplicate tool names
        tool_names = [tool.name for tool in v]
        if len(tool_names) != len(set(tool_names)):
            raise ValueError('Tool names must be unique within an agent')

        return v


class AgentUpdateRequest(BaseModel):
    """Request schema for updating an agent"""
    name: Optional[str] = Field(default=None, description="Updated agent name")
    description: Optional[str] = Field(default=None, description="Updated agent description")
    base_system_prompt: Optional[str] = Field(default=None, description="Updated system prompt")
    is_active: Optional[bool] = Field(default=None, description="Agent active status")
    model_configuration: Optional[ModelConfiguration] = Field(default=None, description="Updated model configuration")

    @validator('name')
    def validate_agent_name(cls, v):
        """Validate agent name if provided"""
        if v is not None and len(v.strip()) < 2:
            raise ValueError('Agent name must be at least 2 characters long')
        return v.strip() if v else v

    @validator('base_system_prompt')
    def validate_system_prompt(cls, v):
        """Validate system prompt if provided"""
        if v is not None and len(v.strip()) < 10:
            raise ValueError('System prompt must be at least 10 characters long')
        return v.strip() if v else v


class ToolsUpdateRequest(BaseModel):
    """Request schema for updating agent tools"""
    tools: List[ToolDefinition] = Field(..., description="Updated tool definitions")

    @validator('tools')
    def validate_tools(cls, v):
        """Validate tool definitions"""
        # Check for duplicate tool names
        tool_names = [tool.name for tool in v]
        if len(tool_names) != len(set(tool_names)):
            raise ValueError('Tool names must be unique within an agent')

        return v


# Response Schemas

class UsageMetrics(BaseModel):
    """Agent usage metrics"""
    total_sessions: int = Field(default=0, description="Total sessions created")
    active_sessions: int = Field(default=0, description="Currently active sessions")
    total_messages: int = Field(default=0, description="Total messages processed")
    total_tool_calls: int = Field(default=0, description="Total tool executions")
    last_used_at: Optional[datetime] = Field(default=None, description="Last time agent was used")
    avg_response_time_ms: Optional[float] = Field(default=None, description="Average response time")


class AgentResponse(BaseModel):
    """Complete agent information response"""
    id: str = Field(..., description="Unique agent identifier")
    app_name: str = Field(..., description="Application name")
    name: str = Field(..., description="Human-readable agent name")
    description: Optional[str] = Field(default=None, description="Agent description")
    base_system_prompt: str = Field(..., description="Base system prompt")
    tools: List[ToolDefinition] = Field(default=[], description="Agent tool definitions")
    model_configuration: ModelConfiguration = Field(..., description="Model configuration")
    status: AgentStatus = Field(..., description="Agent operational status")
    health: HealthStatus = Field(..., description="Agent health status")
    is_active: bool = Field(..., description="Whether agent is active")
    version: int = Field(..., description="Configuration version for optimistic locking")
    usage_metrics: Optional[UsageMetrics] = Field(default=None, description="Usage statistics")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    """Response for listing agents with pagination"""
    agents: List[AgentResponse] = Field(..., description="List of agents")
    total: int = Field(..., description="Total number of agents")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


class AgentSummary(BaseModel):
    """Lightweight agent summary for listings"""
    id: str = Field(..., description="Unique agent identifier")
    app_name: str = Field(..., description="Application name")
    name: str = Field(..., description="Human-readable agent name")
    description: Optional[str] = Field(default=None, description="Agent description")
    status: AgentStatus = Field(..., description="Agent operational status")
    health: HealthStatus = Field(..., description="Agent health status")
    tools_count: int = Field(..., description="Number of configured tools")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_used_at: Optional[datetime] = Field(default=None, description="Last usage timestamp")


# Tool Management Schemas

class ToolValidationResult(BaseModel):
    """Tool validation result"""
    tool_name: str = Field(..., description="Tool name")
    is_valid: bool = Field(..., description="Whether tool passed validation")
    connectivity_check: bool = Field(..., description="Endpoint connectivity status")
    schema_validation: bool = Field(..., description="Schema validation status")
    response_time_ms: Optional[float] = Field(default=None, description="Response time in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error details if validation failed")
    last_checked_at: datetime = Field(..., description="Validation timestamp")


class ToolHealthReport(BaseModel):
    """Complete tool health report for an agent"""
    agent_id: str = Field(..., description="Agent identifier")
    total_tools: int = Field(..., description="Total number of tools")
    healthy_tools: int = Field(..., description="Number of healthy tools")
    unhealthy_tools: int = Field(..., description="Number of unhealthy tools")
    tool_results: List[ToolValidationResult] = Field(..., description="Individual tool validation results")
    overall_health: HealthStatus = Field(..., description="Overall tool health status")
    last_checked_at: datetime = Field(..., description="Health check timestamp")


# Error Response Schemas

class ValidationError(BaseModel):
    """Validation error details"""
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Validation error message")
    value: Any = Field(..., description="Invalid value")


class ErrorResponse(BaseModel):
    """Standard error response"""
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Union[str, List[ValidationError]]] = Field(default=None, description="Additional error details")
    correlation_id: Optional[str] = Field(default=None, description="Request correlation ID for tracing")


# Query Parameter Schemas

class AgentListQuery(BaseModel):
    """Query parameters for listing agents"""
    app_name: Optional[str] = Field(default=None, description="Filter by application name")
    status: Optional[AgentStatus] = Field(default=None, description="Filter by agent status")
    health: Optional[HealthStatus] = Field(default=None, description="Filter by health status")
    search: Optional[str] = Field(default=None, description="Search in name and description")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: str = Field(default="created_at", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")

    @validator('sort_by')
    def validate_sort_by(cls, v):
        """Validate sort field"""
        allowed_fields = ["created_at", "updated_at", "name", "app_name", "last_used_at"]
        if v not in allowed_fields:
            raise ValueError(f'Sort field must be one of: {", ".join(allowed_fields)}')
        return v

    @validator('sort_order')
    def validate_sort_order(cls, v):
        """Validate sort order"""
        if v.lower() not in ["asc", "desc"]:
            raise ValueError('Sort order must be "asc" or "desc"')
        return v.lower()


# Success Response Schemas

class AgentCreatedResponse(BaseModel):
    """Response for successful agent creation"""
    agent_id: str = Field(..., description="Created agent identifier")
    message: str = Field(..., description="Success message")
    agent: AgentResponse = Field(..., description="Created agent details")


class AgentUpdatedResponse(BaseModel):
    """Response for successful agent update"""
    agent_id: str = Field(..., description="Updated agent identifier")
    message: str = Field(..., description="Success message")
    version: int = Field(..., description="New configuration version")
    changes: List[str] = Field(..., description="List of fields that were updated")


class OperationResponse(BaseModel):
    """Generic operation response"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation result message")
    correlation_id: Optional[str] = Field(default=None, description="Request correlation ID")