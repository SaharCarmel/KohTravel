"""
Base tool interface and common tool implementations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class ToolResult(BaseModel):
    """Result from tool execution"""
    success: bool
    content: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    execution_time: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    def dict(self, **kwargs) -> Dict[str, Any]:
        """Convert to dictionary with timestamp formatting"""
        data = super().dict(**kwargs)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class ToolParameter(BaseModel):
    """Tool parameter definition"""
    name: str
    type: str  # "string", "integer", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    properties: Optional[Dict[str, 'ToolParameter']] = None  # For object types


class Tool(ABC):
    """
    Abstract base class for agent tools
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self._parameters: List[ToolParameter] = []
    
    def add_parameter(
        self,
        name: str,
        param_type: str,
        description: str,
        required: bool = True,
        default: Optional[Any] = None,
        enum: Optional[List[Any]] = None
    ) -> 'Tool':
        """Add a parameter to the tool"""
        param = ToolParameter(
            name=name,
            type=param_type,
            description=description,
            required=required,
            default=default,
            enum=enum
        )
        self._parameters.append(param)
        return self
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Get JSON schema for tool parameters"""
        if not self._parameters:
            return {
                "type": "object",
                "properties": {},
                "required": []
            }
        
        properties = {}
        required = []
        
        for param in self._parameters:
            prop_schema = {
                "type": param.type,
                "description": param.description
            }
            
            if param.enum:
                prop_schema["enum"] = param.enum
            
            if param.default is not None:
                prop_schema["default"] = param.default
            
            properties[param.name] = prop_schema
            
            if param.required:
                required.append(param.name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate parameters against schema"""
        schema = self.get_parameters_schema()
        required_params = schema.get("required", [])
        
        # Check required parameters
        for param_name in required_params:
            if param_name not in parameters:
                raise ValueError(f"Required parameter '{param_name}' missing")
        
        # Check parameter types (basic validation)
        properties = schema.get("properties", {})
        for param_name, value in parameters.items():
            if param_name in properties:
                expected_type = properties[param_name]["type"]
                if not self._validate_type(value, expected_type):
                    raise ValueError(f"Parameter '{param_name}' has invalid type")
        
        return True
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Basic type validation"""
        type_mapping = {
            "string": str,
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        if expected_type not in type_mapping:
            return True  # Skip validation for unknown types
        
        return isinstance(value, type_mapping[expected_type])
    
    @abstractmethod
    async def execute(
        self, 
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Execute the tool with given parameters
        
        Args:
            parameters: Tool parameters
            context: Execution context (session info, user data, etc.)
            
        Returns:
            ToolResult with execution outcome
        """
        pass
    
    async def safe_execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Execute tool with error handling and validation
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate parameters
            self.validate_parameters(parameters)
            
            # Execute tool
            result = await self.execute(parameters, context)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            result.execution_time = execution_time
            
            logger.info(
                "Tool executed successfully",
                tool=self.name,
                execution_time=execution_time,
                success=result.success
            )
            
            return result
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            error_result = ToolResult(
                success=False,
                content=f"Tool execution failed: {str(e)}",
                error=str(e),
                execution_time=execution_time,
                metadata={"parameters": parameters}
            )
            
            logger.error(
                "Tool execution failed",
                tool=self.name,
                error=str(e),
                execution_time=execution_time
            )
            
            return error_result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary representation"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.get_parameters_schema()
        }