"""
Production-grade logging configuration for agent infrastructure
"""
import logging
import logging.handlers
import structlog
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


def configure_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    enable_json: bool = True,
    enable_file_rotation: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """
    Configure structured logging with rotation for production use
    """
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )
    
    # Set up file handler with rotation
    if enable_file_rotation:
        file_handler = logging.handlers.RotatingFileHandler(
            log_path / "agent.log",
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        logging.getLogger().addHandler(file_handler)
    
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if enable_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


class AgentLogger:
    """
    Production-grade logger for agent operations with minimal overhead
    """
    
    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)
    
    def conversation_started(self, session_id: str, user_message_length: int):
        """Log conversation start"""
        self.logger.info(
            "conversation_started",
            session_id=session_id,
            message_length=user_message_length,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def tool_called(self, session_id: str, tool_name: str, parameters: Dict[str, Any], call_id: str):
        """Log tool execution start"""
        self.logger.info(
            "tool_called",
            session_id=session_id,
            tool_name=tool_name,
            call_id=call_id,
            param_count=len(parameters),
            # Only log parameter keys to avoid sensitive data
            param_keys=list(parameters.keys()) if isinstance(parameters, dict) else None
        )
    
    def tool_completed(self, session_id: str, tool_name: str, call_id: str, 
                      success: bool, duration_ms: int, result_length: int = 0, error: str = None):
        """Log tool execution completion"""
        log_data = {
            "tool_completed": True,
            "session_id": session_id,
            "tool_name": tool_name,
            "call_id": call_id,
            "success": success,
            "duration_ms": duration_ms,
            "result_length": result_length
        }
        
        if error:
            log_data["error"] = error
            self.logger.error("tool_completed", **log_data)
        else:
            self.logger.info("tool_completed", **log_data)
    
    def search_executed(self, session_id: str, query: str, results_count: int, duration_ms: int):
        """Log search operations"""
        self.logger.info(
            "search_executed",
            session_id=session_id,
            query_length=len(query),
            results_count=results_count,
            duration_ms=duration_ms
        )
    
    def conversation_completed(self, session_id: str, turn_count: int, total_duration_ms: int, 
                             tool_calls_count: int, success: bool):
        """Log conversation completion"""
        self.logger.info(
            "conversation_completed",
            session_id=session_id,
            turn_count=turn_count,
            total_duration_ms=total_duration_ms,
            tool_calls_count=tool_calls_count,
            success=success
        )
    
    def error_occurred(self, session_id: str, error_type: str, error_message: str, context: Dict[str, Any] = None):
        """Log errors with context"""
        log_data = {
            "error_occurred": True,
            "session_id": session_id,
            "error_type": error_type,
            "error_message": error_message
        }
        
        if context:
            log_data.update(context)
        
        self.logger.error("agent_error", **log_data)
    
    def performance_warning(self, operation: str, duration_ms: int, threshold_ms: int, context: Dict[str, Any] = None):
        """Log performance warnings"""
        log_data = {
            "performance_warning": True,
            "operation": operation,
            "duration_ms": duration_ms,
            "threshold_ms": threshold_ms,
            "slowdown_factor": duration_ms / threshold_ms
        }
        
        if context:
            log_data.update(context)
        
        self.logger.warning("performance_warning", **log_data)


# Global logger instances
agent_logger = AgentLogger("agent")
tool_logger = AgentLogger("tools")
api_logger = AgentLogger("api")