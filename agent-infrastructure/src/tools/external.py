"""
External tool system for calling project-specific APIs
"""
import httpx
import time
from typing import Dict, Any, Optional, List
import structlog

from src.tools.base import Tool, ToolResult
from src.core.logging_config import tool_logger

logger = structlog.get_logger(__name__)


class ExternalTool(Tool):
    """
    Tool that calls external HTTP APIs for project-specific functionality
    """
    
    def __init__(
        self, 
        name: str, 
        description: str,
        endpoint_url: str,
        parameters_schema: Dict[str, Any],
        method: str = "POST",
        timeout: int = 30
    ):
        super().__init__(name, description)
        self.endpoint_url = endpoint_url
        self.method = method.upper()
        self.timeout = timeout
        
        # Set parameters from schema
        if "properties" in parameters_schema:
            required = parameters_schema.get("required", [])
            for param_name, param_def in parameters_schema["properties"].items():
                self.add_parameter(
                    name=param_name,
                    param_type=param_def["type"],
                    description=param_def["description"],
                    required=param_name in required,
                    default=param_def.get("default"),
                    enum=param_def.get("enum")
                )
    
    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Execute external tool via HTTP call"""
        
        start_time = time.time()
        session_id = context.get("session_id", "unknown") if context else "unknown"
        
        try:
            # Prepare request payload
            payload = {
                "user_id": context.get("user_id") if context else None,
                "parameters": parameters
            }
            
            # Make HTTP request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if self.method == "POST":
                    response = await client.post(
                        self.endpoint_url,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                elif self.method == "GET":
                    response = await client.get(
                        self.endpoint_url,
                        params=parameters
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {self.method}")
                
                response.raise_for_status()
                result_data = response.json()
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log search-specific operations
                if self.name == "search_documents" and parameters.get("query"):
                    results_count = result_data.get("metadata", {}).get("count", 0)
                    tool_logger.search_executed(
                        session_id=session_id,
                        query=parameters["query"],
                        results_count=results_count,
                        duration_ms=duration_ms
                    )
                
                # Handle response format
                if isinstance(result_data, dict) and "success" in result_data:
                    # Standard tool response format
                    return ToolResult(
                        success=result_data.get("success", False),
                        content=result_data.get("content", ""),
                        metadata=result_data.get("metadata", {}),
                        error=result_data.get("error")
                    )
                else:
                    # Raw response
                    return ToolResult(
                        success=True,
                        content=f"External tool executed successfully",
                        metadata={"response": result_data}
                    )
                
        except httpx.HTTPError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "External tool HTTP error",
                tool=self.name,
                error=str(e),
                endpoint=self.endpoint_url,
                duration_ms=duration_ms
            )
            return ToolResult(
                success=False,
                content=f"HTTP error calling external tool: {str(e)}",
                error=f"http_error: {str(e)}"
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "External tool execution error",
                tool=self.name,
                error=str(e),
                endpoint=self.endpoint_url,
                duration_ms=duration_ms
            )
            return ToolResult(
                success=False,
                content=f"External tool execution failed: {str(e)}",
                error=str(e)
            )


class ExternalToolRegistry:
    """
    Registry for loading external tools from project APIs
    """
    
    def __init__(self):
        self.tools: Dict[str, ExternalTool] = {}
    
    async def load_tools_from_endpoint(
        self, 
        base_url: str,
        tools_endpoint: str = "/available_tools",
        tools_prefix: str = ""
    ) -> List[ExternalTool]:
        """
        Load tools from external API endpoint
        
        Expected format:
        [
            {
                "name": "tool_name",
                "description": "Tool description",
                "parameters": {...json_schema...}
            },
            ...
        ]
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{base_url}{tools_endpoint}")
                response.raise_for_status()
                
                tools_data = response.json()
                loaded_tools = []
                
                for tool_def in tools_data:
                    tool_name = tool_def["name"]
                    
                    # Create external tool
                    tool = ExternalTool(
                        name=tool_name,
                        description=tool_def["description"],
                        endpoint_url=f"{base_url}{tools_prefix}/{tool_name}",
                        parameters_schema=tool_def["parameters"]
                    )
                    
                    self.tools[tool_name] = tool
                    loaded_tools.append(tool)
                    
                    logger.info(
                        "Loaded external tool",
                        tool_name=tool_name,
                        endpoint=tool.endpoint_url
                    )
                
                return loaded_tools
                
        except Exception as e:
            logger.error(
                "Failed to load external tools",
                base_url=base_url,
                error=str(e)
            )
            return []
    
    
    def get_tool(self, name: str) -> Optional[ExternalTool]:
        """Get tool by name"""
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[ExternalTool]:
        """Get all registered tools"""
        return list(self.tools.values())
    
    def clear(self):
        """Clear all registered tools"""
        self.tools.clear()


# Global registry instance
external_registry = ExternalToolRegistry()