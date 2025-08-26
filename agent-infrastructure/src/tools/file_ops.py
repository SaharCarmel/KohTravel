"""
File operation tools for agents
"""
import os
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional, List
import structlog

from src.tools.base import Tool, ToolResult

logger = structlog.get_logger(__name__)


class ReadFileTool(Tool):
    """
    Tool for reading file contents
    """
    
    def __init__(self, allowed_paths: Optional[List[str]] = None):
        super().__init__(
            name="read_file",
            description="Read contents of a text file"
        )
        
        self.allowed_paths = allowed_paths or []
        
        # Add parameters
        self.add_parameter(
            name="file_path",
            param_type="string",
            description="Path to the file to read",
            required=True
        ).add_parameter(
            name="max_chars",
            param_type="integer",
            description="Maximum number of characters to read",
            required=False,
            default=10000
        )
    
    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Read file contents"""
        
        file_path = parameters["file_path"]
        max_chars = parameters.get("max_chars", 10000)
        
        # Security check
        if not self._is_allowed_path(file_path):
            return ToolResult(
                success=False,
                content=f"File path '{file_path}' is not allowed",
                error="forbidden_path"
            )
        
        try:
            path = Path(file_path)
            
            if not path.exists():
                return ToolResult(
                    success=False,
                    content=f"File not found: {file_path}",
                    error="file_not_found"
                )
            
            if not path.is_file():
                return ToolResult(
                    success=False,
                    content=f"Path is not a file: {file_path}",
                    error="not_a_file"
                )
            
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read(max_chars)
            
            file_size = path.stat().st_size
            truncated = len(content) >= max_chars
            
            return ToolResult(
                success=True,
                content=f"File read successfully. Size: {file_size} bytes" + 
                       (" (truncated)" if truncated else ""),
                metadata={
                    "file_path": file_path,
                    "content": content,
                    "file_size": file_size,
                    "truncated": truncated,
                    "chars_read": len(content)
                }
            )
            
        except Exception as e:
            logger.error("File read failed", error=str(e), file_path=file_path)
            return ToolResult(
                success=False,
                content=f"Failed to read file: {str(e)}",
                error=str(e)
            )
    
    def _is_allowed_path(self, file_path: str) -> bool:
        """Check if file path is allowed"""
        if not self.allowed_paths:
            return True  # No restrictions
        
        abs_path = os.path.abspath(file_path)
        
        for allowed in self.allowed_paths:
            allowed_abs = os.path.abspath(allowed)
            if abs_path.startswith(allowed_abs):
                return True
        
        return False


class WriteFileTool(Tool):
    """
    Tool for writing file contents
    """
    
    def __init__(self, allowed_paths: Optional[List[str]] = None):
        super().__init__(
            name="write_file",
            description="Write content to a file"
        )
        
        self.allowed_paths = allowed_paths or []
        
        # Add parameters
        self.add_parameter(
            name="file_path",
            param_type="string",
            description="Path to the file to write",
            required=True
        ).add_parameter(
            name="content",
            param_type="string",
            description="Content to write to the file",
            required=True
        ).add_parameter(
            name="mode",
            param_type="string",
            description="Write mode: 'write' (overwrite) or 'append'",
            required=False,
            default="write",
            enum=["write", "append"]
        )
    
    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Write file contents"""
        
        file_path = parameters["file_path"]
        content = parameters["content"]
        mode = parameters.get("mode", "write")
        
        # Security check
        if not self._is_allowed_path(file_path):
            return ToolResult(
                success=False,
                content=f"File path '{file_path}' is not allowed",
                error="forbidden_path"
            )
        
        try:
            path = Path(file_path)
            
            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Determine file mode
            file_mode = 'a' if mode == 'append' else 'w'
            
            async with aiofiles.open(file_path, file_mode, encoding='utf-8') as f:
                await f.write(content)
            
            file_size = path.stat().st_size
            
            return ToolResult(
                success=True,
                content=f"File {'appended to' if mode == 'append' else 'written'} successfully. " +
                       f"Size: {file_size} bytes",
                metadata={
                    "file_path": file_path,
                    "file_size": file_size,
                    "mode": mode,
                    "content_length": len(content)
                }
            )
            
        except Exception as e:
            logger.error("File write failed", error=str(e), file_path=file_path)
            return ToolResult(
                success=False,
                content=f"Failed to write file: {str(e)}",
                error=str(e)
            )
    
    def _is_allowed_path(self, file_path: str) -> bool:
        """Check if file path is allowed"""
        if not self.allowed_paths:
            return True  # No restrictions
        
        abs_path = os.path.abspath(file_path)
        
        for allowed in self.allowed_paths:
            allowed_abs = os.path.abspath(allowed)
            if abs_path.startswith(allowed_abs):
                return True
        
        return False


class ListDirectoryTool(Tool):
    """
    Tool for listing directory contents
    """
    
    def __init__(self, allowed_paths: Optional[List[str]] = None):
        super().__init__(
            name="list_directory",
            description="List contents of a directory"
        )
        
        self.allowed_paths = allowed_paths or []
        
        # Add parameters
        self.add_parameter(
            name="directory_path",
            param_type="string",
            description="Path to the directory to list",
            required=True
        ).add_parameter(
            name="include_hidden",
            param_type="boolean",
            description="Include hidden files (starting with .)",
            required=False,
            default=False
        ).add_parameter(
            name="file_types_only",
            param_type="array",
            description="Only include files with these extensions",
            required=False
        )
    
    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """List directory contents"""
        
        directory_path = parameters["directory_path"]
        include_hidden = parameters.get("include_hidden", False)
        file_types_only = parameters.get("file_types_only", [])
        
        # Security check
        if not self._is_allowed_path(directory_path):
            return ToolResult(
                success=False,
                content=f"Directory path '{directory_path}' is not allowed",
                error="forbidden_path"
            )
        
        try:
            path = Path(directory_path)
            
            if not path.exists():
                return ToolResult(
                    success=False,
                    content=f"Directory not found: {directory_path}",
                    error="directory_not_found"
                )
            
            if not path.is_dir():
                return ToolResult(
                    success=False,
                    content=f"Path is not a directory: {directory_path}",
                    error="not_a_directory"
                )
            
            items = []
            for item in path.iterdir():
                # Skip hidden files if not requested
                if not include_hidden and item.name.startswith('.'):
                    continue
                
                # Filter by file types if specified
                if file_types_only and item.is_file():
                    if not any(item.name.endswith(ext) for ext in file_types_only):
                        continue
                
                item_info = {
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                    "modified": item.stat().st_mtime
                }
                items.append(item_info)
            
            # Sort by name
            items.sort(key=lambda x: x["name"])
            
            return ToolResult(
                success=True,
                content=f"Listed {len(items)} items in {directory_path}",
                metadata={
                    "directory_path": directory_path,
                    "items": items,
                    "count": len(items),
                    "include_hidden": include_hidden,
                    "file_types_filter": file_types_only
                }
            )
            
        except Exception as e:
            logger.error("Directory listing failed", error=str(e), path=directory_path)
            return ToolResult(
                success=False,
                content=f"Failed to list directory: {str(e)}",
                error=str(e)
            )
    
    def _is_allowed_path(self, directory_path: str) -> bool:
        """Check if directory path is allowed"""
        if not self.allowed_paths:
            return True  # No restrictions
        
        abs_path = os.path.abspath(directory_path)
        
        for allowed in self.allowed_paths:
            allowed_abs = os.path.abspath(allowed)
            if abs_path.startswith(allowed_abs):
                return True
        
        return False