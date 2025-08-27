"""
Configuration settings for agent infrastructure
"""
import os
from typing import List, Optional
from pydantic import validator
from pydantic_settings import BaseSettings
import structlog

logger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    """Application settings"""
    
    # Basic settings
    debug: bool = False
    environment: str = "development"
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8001
    cors_origins: str = "*"
    
    # Authentication
    auth_enabled: bool = False
    api_key: Optional[str] = None
    
    # LLM Provider settings
    anthropic_api_key: str
    default_model: str = "claude-3-5-sonnet-20241022"
    
    # Database settings
    database_url: Optional[str] = None
    
    # Service URLs
    main_api_url: str = "http://localhost:8000"
    
    # File access settings
    allowed_file_paths: List[str] = []
    allow_file_write: bool = False
    
    # Logging settings
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def get_cors_origins_list(self) -> List[str]:
        """Parse CORS origins into list"""
        if not self.cors_origins:
            return ["*"]
        
        v = self.cors_origins.strip()
        if v == "*":
            return ["*"]
        
        # Handle JSON array format
        if v.startswith('[') and v.endswith(']'):
            try:
                import json
                return json.loads(v)
            except:
                pass
        
        # Handle comma-separated format
        return [origin.strip() for origin in v.split(",") if origin.strip()]
    
    @validator("allowed_file_paths", pre=True)
    def parse_file_paths(cls, v):
        if isinstance(v, str):
            return [path.strip() for path in v.split(",") if path.strip()]
        return v
    
    @validator("anthropic_api_key")
    def validate_anthropic_key(cls, v):
        if not v or not v.startswith("sk-"):
            raise ValueError("Invalid Anthropic API key")
        return v
    
    def configure_logging(self):
        """Configure structured logging"""
        import structlog
        
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton)"""
    global _settings
    
    if _settings is None:
        _settings = Settings()
        _settings.configure_logging()
        
        logger.info(
            "Settings loaded",
            environment=_settings.environment,
            debug=_settings.debug,
            auth_enabled=_settings.auth_enabled,
            database_configured=_settings.database_url is not None,
            file_write_enabled=_settings.allow_file_write
        )
    
    return _settings


def load_project_config(project_name: str) -> dict:
    """Load project-specific configuration"""
    config_path = f"configs/{project_name}.yaml"
    
    if not os.path.exists(config_path):
        logger.warning("Project config not found", project=project_name, path=config_path)
        return {}
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info("Project config loaded", project=project_name, config_keys=list(config.keys()))
        return config
        
    except Exception as e:
        logger.error("Failed to load project config", project=project_name, error=str(e))
        return {}