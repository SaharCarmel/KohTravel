"""
Enhanced Tool Registry Core System

This module implements the comprehensive tool registry system for dynamic tool management,
building upon the existing ExternalToolRegistry foundation while adding database-driven
configuration, health monitoring, and advanced validation capabilities.

Key Features:
- Dynamic tool registration and deregistration
- Multi-level caching with TTL
- Tool health monitoring with circuit breaker pattern
- Security validation pipeline
- Performance metrics tracking
- Database integration with fallback to legacy configuration
"""

import asyncio
import time
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from cachetools import TTLCache
import httpx
import structlog

from src.schemas.tool_schemas import (
    ToolDefinition, ToolRegistrationRequest, ToolUpdateRequest,
    ToolValidationResult, ToolHealthCheckResult, ToolMetrics,
    ToolStatus, ToolHealthStatus, ToolType, SecurityLevel,
    ToolSecurityPolicy
)
from src.tools.external import ExternalTool, ExternalToolRegistry
from src.tools.base import Tool, ToolResult
from src.config.settings import get_settings

logger = structlog.get_logger(__name__)


class CircuitBreaker:
    """Circuit breaker pattern for tool execution reliability"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open

    def is_open(self) -> bool:
        """Check if circuit breaker is open (blocking requests)"""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                return False
            return True
        return False

    def record_success(self):
        """Record successful execution"""
        self.failure_count = 0
        if self.state == "half_open":
            self.state = "closed"

    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class ToolValidator:
    """Comprehensive tool validation pipeline"""

    def __init__(self):
        self.settings = get_settings()
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5)
        )

    async def validate_tool_registration(self, tool_request: ToolRegistrationRequest) -> ToolValidationResult:
        """
        Comprehensive tool validation pipeline
        """
        result = ToolValidationResult(
            tool_id="",
            tool_name=tool_request.name,
            is_valid=False,
            connectivity_check=False,
            schema_validation=False,
            security_validation=False,
            last_validated_at=datetime.now(timezone.utc)
        )

        try:
            # Stage 1: Schema validation
            if not await self._validate_tool_schema(tool_request):
                result.error_details = ["Invalid tool schema structure"]
                return result
            result.schema_validation = True

            # Stage 2: Security policy validation
            if not await self._validate_security_policy(tool_request.security_policy):
                result.error_details = ["Security policy validation failed"]
                return result
            result.security_validation = True

            # Stage 3: Endpoint connectivity check (for external tools)
            if tool_request.type == ToolType.EXTERNAL and tool_request.endpoint_url:
                connectivity_result = await self._validate_endpoint_connectivity(tool_request.endpoint_url)
                result.connectivity_check = connectivity_result.success
                result.response_time_ms = connectivity_result.metadata.get("response_time_ms")

                if not connectivity_result.success:
                    result.error_details = [f"Endpoint connectivity failed: {connectivity_result.error}"]
                    return result
            else:
                result.connectivity_check = True  # Not applicable for internal tools

            # Stage 4: Domain whitelist validation
            if tool_request.endpoint_url and not await self._validate_domain_whitelist(tool_request.endpoint_url):
                result.error_details = ["Domain not in allowed whitelist"]
                return result

            result.is_valid = True
            logger.info(
                "Tool validation successful",
                tool_name=tool_request.name,
                validation_time_ms=result.response_time_ms
            )

        except Exception as e:
            logger.error("Tool validation error", tool_name=tool_request.name, error=str(e))
            result.error_details = [f"Validation error: {str(e)}"]

        return result

    async def _validate_tool_schema(self, tool_request: ToolRegistrationRequest) -> bool:
        """Validate tool schema structure"""
        try:
            # Basic validation - name, type, description required
            if not tool_request.name or not tool_request.type or not tool_request.description:
                return False

            # Validate input/output schemas if provided
            if tool_request.input_schema:
                # Ensure schema has required structure
                if not tool_request.input_schema.type:
                    return False

            return True
        except Exception as e:
            logger.warning("Schema validation error", error=str(e))
            return False

    async def _validate_security_policy(self, security_policy: Optional[ToolSecurityPolicy]) -> bool:
        """Validate security policy settings"""
        if not security_policy:
            return True  # Default policy is acceptable

        try:
            # Validate timeout range
            if not (1 <= security_policy.timeout_seconds <= 300):
                return False

            # Validate rate limits
            if not (1 <= security_policy.rate_limit_per_minute <= 1000):
                return False

            # Validate request/response size limits
            if security_policy.max_request_size > 100 * 1024 * 1024:  # 100MB max
                return False

            if security_policy.max_response_size > 500 * 1024 * 1024:  # 500MB max
                return False

            return True
        except Exception as e:
            logger.warning("Security policy validation error", error=str(e))
            return False

    async def _validate_endpoint_connectivity(self, endpoint_url: str) -> ToolResult:
        """Test endpoint connectivity and basic response"""
        start_time = time.time()

        try:
            # Perform health check request
            response = await self.http_client.get(
                f"{endpoint_url}/health",
                timeout=5.0
            )

            response_time_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return ToolResult(
                    success=True,
                    content="Endpoint connectivity verified",
                    metadata={"response_time_ms": response_time_ms}
                )
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Endpoint returned status {response.status_code}",
                    metadata={"response_time_ms": response_time_ms}
                )

        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                content="",
                error="Endpoint connection timeout",
                metadata={"response_time_ms": (time.time() - start_time) * 1000}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Connectivity check failed: {str(e)}",
                metadata={"response_time_ms": (time.time() - start_time) * 1000}
            )

    async def _validate_domain_whitelist(self, endpoint_url: str) -> bool:
        """Validate endpoint domain against whitelist"""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(endpoint_url)
            domain = parsed.netloc.lower()

            # Get allowed domains from settings
            allowed_domains = getattr(self.settings, 'allowed_tool_domains', [])
            if not allowed_domains:
                # If no whitelist configured, allow localhost and common development domains
                allowed_domains = ['localhost', '127.0.0.1', '::1']

            # Check if domain or any parent domain is allowed
            for allowed in allowed_domains:
                if domain == allowed or domain.endswith(f'.{allowed}'):
                    return True

            logger.warning("Domain not in whitelist", domain=domain, allowed_domains=allowed_domains)
            return False

        except Exception as e:
            logger.error("Domain validation error", endpoint_url=endpoint_url, error=str(e))
            return False

    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()


class ToolHealthMonitor:
    """Background tool health monitoring service"""

    def __init__(self, registry: 'ToolRegistryCore'):
        self.registry = registry
        self.monitor_interval = 300  # 5 minutes
        self.running = False
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=3.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=3)
        )

    async def start_monitoring(self):
        """Start background health monitoring"""
        if self.running:
            return

        self.running = True
        logger.info("Starting tool health monitoring", interval_seconds=self.monitor_interval)

        # Start monitoring task
        asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self):
        """Stop background health monitoring"""
        self.running = False
        await self.http_client.aclose()
        logger.info("Stopped tool health monitoring")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                await self._check_all_tools_health()
                await asyncio.sleep(self.monitor_interval)
            except Exception as e:
                logger.error("Health monitoring error", error=str(e))
                await asyncio.sleep(60)  # Shorter retry interval on error

    async def _check_all_tools_health(self):
        """Check health of all registered tools"""
        tools = await self.registry.get_all_tools()

        # Check tools concurrently with rate limiting
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent health checks

        async def check_tool_with_semaphore(tool):
            async with semaphore:
                return await self.check_tool_health(tool.name)

        tasks = [check_tool_with_semaphore(tool) for tool in tools if tool.type == ToolType.EXTERNAL]

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            healthy_count = sum(1 for r in results if isinstance(r, ToolHealthCheckResult) and r.health_status == ToolHealthStatus.HEALTHY)
            total_count = len(tasks)

            logger.info(
                "Health check completed",
                healthy_tools=healthy_count,
                total_tools=total_count,
                health_percentage=round((healthy_count / total_count) * 100, 2) if total_count > 0 else 100
            )

    async def check_tool_health(self, tool_name: str) -> ToolHealthCheckResult:
        """Check health of a specific tool"""
        start_time = time.time()

        try:
            tool = await self.registry.get_tool(tool_name)
            if not tool:
                return ToolHealthCheckResult(
                    tool_id=tool_name,
                    tool_name=tool_name,
                    health_status=ToolHealthStatus.UNKNOWN,
                    is_reachable=False,
                    error_message="Tool not found",
                    checked_at=datetime.now(timezone.utc)
                )

            if tool.type != ToolType.EXTERNAL or not tool.endpoint_url:
                # Internal tools are assumed healthy
                return ToolHealthCheckResult(
                    tool_id=tool.id,
                    tool_name=tool_name,
                    health_status=ToolHealthStatus.HEALTHY,
                    is_reachable=True,
                    checked_at=datetime.now(timezone.utc)
                )

            # Check external tool endpoint
            try:
                response = await self.http_client.get(
                    f"{tool.endpoint_url}/health",
                    timeout=5.0
                )

                response_time_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    health_status = ToolHealthStatus.HEALTHY
                    is_reachable = True
                    error_message = None
                elif response.status_code in [503, 502, 504]:
                    health_status = ToolHealthStatus.DEGRADED
                    is_reachable = True
                    error_message = f"Service degraded (status {response.status_code})"
                else:
                    health_status = ToolHealthStatus.UNHEALTHY
                    is_reachable = True
                    error_message = f"Unhealthy status code: {response.status_code}"

                return ToolHealthCheckResult(
                    tool_id=tool.id,
                    tool_name=tool_name,
                    health_status=health_status,
                    is_reachable=is_reachable,
                    response_time_ms=response_time_ms,
                    status_code=response.status_code,
                    error_message=error_message,
                    checked_at=datetime.now(timezone.utc)
                )

            except httpx.TimeoutException:
                return ToolHealthCheckResult(
                    tool_id=tool.id,
                    tool_name=tool_name,
                    health_status=ToolHealthStatus.UNHEALTHY,
                    is_reachable=False,
                    error_message="Connection timeout",
                    checked_at=datetime.now(timezone.utc)
                )
            except httpx.ConnectError:
                return ToolHealthCheckResult(
                    tool_id=tool.id,
                    tool_name=tool_name,
                    health_status=ToolHealthStatus.UNREACHABLE,
                    is_reachable=False,
                    error_message="Connection refused",
                    checked_at=datetime.now(timezone.utc)
                )

        except Exception as e:
            logger.error("Tool health check error", tool_name=tool_name, error=str(e))
            return ToolHealthCheckResult(
                tool_id=tool_name,
                tool_name=tool_name,
                health_status=ToolHealthStatus.UNKNOWN,
                is_reachable=False,
                error_message=f"Health check error: {str(e)}",
                checked_at=datetime.now(timezone.utc)
            )


class ToolRegistryCore:
    """
    Enhanced tool registry with dynamic management, caching, and monitoring.

    This class builds upon the existing ExternalToolRegistry pattern while adding:
    - Database-driven tool configuration
    - Multi-level caching with TTL
    - Health monitoring and circuit breakers
    - Security validation pipeline
    - Performance metrics tracking
    """

    def __init__(self):
        self.settings = get_settings()

        # Multi-level caching system
        self.tool_cache = TTLCache(maxsize=1000, ttl=300)  # 5-minute TTL
        self.agent_tools_cache = TTLCache(maxsize=500, ttl=600)  # 10-minute TTL
        self.health_status_cache = TTLCache(maxsize=2000, ttl=60)  # 1-minute TTL

        # Component initialization
        self.validator = ToolValidator()
        self.health_monitor = ToolHealthMonitor(self)

        # Circuit breakers for external tools
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Legacy external tool registry for fallback
        self.legacy_registry = ExternalToolRegistry()

        # Database connection (will be injected)
        self.db_session = None

        logger.info("ToolRegistryCore initialized")

    async def initialize(self, db_session=None):
        """Initialize registry with database session"""
        self.db_session = db_session

        # Start health monitoring if enabled
        if getattr(self.settings, 'tool_health_monitoring_enabled', True):
            await self.health_monitor.start_monitoring()


    async def shutdown(self):
        """Shutdown registry and cleanup resources"""
        await self.health_monitor.stop_monitoring()
        await self.validator.close()

    # Tool Registration Methods

    async def register_tool(self, tool_request: ToolRegistrationRequest) -> str:
        """Register a new tool with comprehensive validation"""

        # Validate tool
        validation_result = await self.validator.validate_tool_registration(tool_request)
        if not validation_result.is_valid:
            raise ValueError(f"Tool validation failed: {validation_result.error_details}")

        # Generate tool ID
        tool_id = self._generate_tool_id(tool_request.name, tool_request.version)

        # Create tool definition using model_validate to handle Pydantic v2 properly
        tool_data = {
            "id": tool_id,
            "agent_id": "",  # Will be set when assigned to agent
            "name": tool_request.name,
            "type": tool_request.type,
            "description": tool_request.description,
            "endpoint_url": tool_request.endpoint_url,
            "input_schema": tool_request.input_schema.model_dump() if tool_request.input_schema else None,
            "output_schema": tool_request.output_schema.model_dump() if tool_request.output_schema else None,
            "security_policy": (tool_request.security_policy or ToolSecurityPolicy()).model_dump(),
            "status": ToolStatus.ACTIVE,
            "health": ToolHealthStatus.UNKNOWN,
            "enabled": tool_request.enabled,
            "tags": tool_request.tags or [],
            "version": tool_request.version,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        tool_definition = ToolDefinition.model_validate(tool_data)

        # Store in cache
        self.tool_cache[tool_id] = tool_definition

        # Initialize circuit breaker for external tools
        if tool_request.type == ToolType.EXTERNAL:
            self.circuit_breakers[tool_request.name] = CircuitBreaker()

        logger.info(
            "Tool registered successfully",
            tool_id=tool_id,
            tool_name=tool_request.name,
            tool_type=tool_request.type.value
        )

        return tool_id

    async def update_tool(self, tool_id: str, update_request: ToolUpdateRequest) -> bool:
        """Update existing tool configuration"""

        tool = await self.get_tool_by_id(tool_id)
        if not tool:
            return False

        # Update fields
        if update_request.description is not None:
            tool.description = update_request.description
        if update_request.endpoint_url is not None:
            tool.endpoint_url = update_request.endpoint_url
        if update_request.input_schema is not None:
            tool.input_schema = update_request.input_schema
        if update_request.output_schema is not None:
            tool.output_schema = update_request.output_schema
        if update_request.security_policy is not None:
            tool.security_policy = update_request.security_policy
        if update_request.enabled is not None:
            tool.enabled = update_request.enabled
        if update_request.tags is not None:
            tool.tags = update_request.tags
        if update_request.version is not None:
            tool.version = update_request.version

        tool.updated_at = datetime.now(timezone.utc)

        # Update cache
        self.tool_cache[tool_id] = tool

        # Invalidate agent caches that use this tool
        await self._invalidate_related_agent_caches(tool.name)

        return True

    async def deregister_tool(self, tool_id: str) -> bool:
        """Deregister a tool"""

        tool = await self.get_tool_by_id(tool_id)
        if not tool:
            return False

        # Remove from cache
        self.tool_cache.pop(tool_id, None)

        # Remove circuit breaker
        self.circuit_breakers.pop(tool.name, None)

        # Invalidate related caches
        await self._invalidate_related_agent_caches(tool.name)

        return True

    # Tool Retrieval Methods

    async def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get tool by name (latest version)"""

        # Check cache first
        for tool_id, tool in self.tool_cache.items():
            if tool.name == tool_name:
                return tool

        return None  # Database integration placeholder

    async def get_tool_by_id(self, tool_id: str) -> Optional[ToolDefinition]:
        """Get tool by ID"""

        # Check cache first
        if tool_id in self.tool_cache:
            return self.tool_cache[tool_id]

        return None  # Database integration placeholder

    async def get_agent_tools(self, agent_id: str) -> List[ToolDefinition]:
        """
        Get all tools assigned to an agent.

        Implements hybrid loading: database-first with legacy fallback.
        """

        # Check cache first
        cache_key = f"agent_tools:{agent_id}"
        if cache_key in self.agent_tools_cache:
            return self.agent_tools_cache[cache_key]

        tools = []

        # Try dynamic loading if enabled
        if getattr(self.settings, 'dynamic_tool_management_enabled', False):
            tools = await self._load_agent_tools_from_database(agent_id)

            if tools:
                logger.info(
                    "Loaded tools from dynamic registry",
                    agent_id=agent_id,
                    tool_count=len(tools)
                )

        # Fallback to legacy loading if no dynamic tools or disabled
        if not tools:
            tools = await self._load_agent_tools_legacy(agent_id)
            logger.info(
                "Using legacy tool loading",
                agent_id=agent_id,
                tool_count=len(tools)
            )

        # Cache result
        self.agent_tools_cache[cache_key] = tools

        return tools

    async def get_all_tools(self) -> List[ToolDefinition]:
        """Get all registered tools"""
        return list(self.tool_cache.values())

    # Tool Health and Validation Methods

    async def validate_tool_health(self, tool: ToolDefinition) -> bool:
        """Validate tool health for use in agent"""
        # Check circuit breaker
        if tool.name in self.circuit_breakers and self.circuit_breakers[tool.name].is_open():
            logger.warning("Tool circuit breaker open", tool_name=tool.name)
            return False

        # Internal tools are assumed healthy
        if tool.type != ToolType.EXTERNAL:
            return True

        # Get health status and check if acceptable
        health_status = await self.get_tool_health_status(tool.name)
        return health_status in [ToolHealthStatus.HEALTHY, ToolHealthStatus.DEGRADED]

    async def get_tool_health_status(self, tool_name: str) -> ToolHealthStatus:
        """Get current health status of a tool"""
        health_key = f"health:{tool_name}"
        if health_key in self.health_status_cache:
            return self.health_status_cache[health_key]

        # Perform health check and cache result
        health_result = await self.health_monitor.check_tool_health(tool_name)
        self.health_status_cache[health_key] = health_result.health_status
        return health_result.health_status

    # Cache Management Methods

    async def invalidate_agent_cache(self, agent_id: str):
        """Invalidate cached tools for specific agent"""
        cache_key = f"agent_tools:{agent_id}"
        self.agent_tools_cache.pop(cache_key, None)

    async def _invalidate_related_agent_caches(self, tool_name: str):
        """Invalidate all agent caches that might use this tool"""
        # Since we don't have reverse mapping, clear all agent caches
        # In production, implement more sophisticated cache invalidation
        self.agent_tools_cache.clear()

    # Private Helper Methods

    def _generate_tool_id(self, name: str, version: str) -> str:
        """Generate unique tool ID"""
        timestamp = int(time.time())
        content = f"{name}:{version}:{timestamp}"
        hash_obj = hashlib.sha256(content.encode())
        return f"tool_{hash_obj.hexdigest()[:16]}"

    async def _load_agent_tools_from_database(self, agent_id: str) -> List[ToolDefinition]:
        """Load tools from database (placeholder for future implementation)"""
        return []  # Database integration placeholder

    async def _load_agent_tools_legacy(self, agent_id: str) -> List[ToolDefinition]:
        """Load tools using legacy configuration patterns"""

        # Extract project from agent_id (assuming format "project-agent-userid")
        project = agent_id.split('-')[0] if '-' in agent_id else agent_id

        # Use existing legacy configuration
        import os
        api_url = os.getenv('MAIN_API_URL', 'http://localhost:8000')

        external_tools_config = {
            "kohtravel": f"{api_url}/api/agent/tools"
        }

        if project in external_tools_config:
            tools_base_url = external_tools_config[project]
            try:
                # Load using existing external registry
                external_tools = await self.legacy_registry.load_tools_from_endpoint(tools_base_url)

                # Convert to ToolDefinition format
                tool_definitions = []
                for ext_tool in external_tools:
                    tool_def = ToolDefinition(
                        id=f"legacy_{ext_tool.name}",
                        agent_id=agent_id,
                        name=ext_tool.name,
                        type=ToolType.EXTERNAL,
                        description=ext_tool.description,
                        endpoint_url=ext_tool.endpoint_url,
                        security_policy=ToolSecurityPolicy(),  # Default policy
                        status=ToolStatus.ACTIVE,
                        health=ToolHealthStatus.UNKNOWN,
                        enabled=True,
                        tags=["legacy"],
                        version="1.0.0",
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    tool_definitions.append(tool_def)

                return tool_definitions

            except Exception as e:
                logger.warning("Failed to load legacy tools", project=project, error=str(e))

        return []


# Global registry instance
tool_registry = ToolRegistryCore()