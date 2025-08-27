"""
Shared configuration for KohTravel2 services
Handles development port offsets and production URL resolution
"""
import os
from typing import Dict, Optional


def get_service_urls() -> Dict[str, str]:
    """
    Get service URLs for current environment
    
    Production (Vercel): All services on same domain
    Development: Separate services with configurable port offsets
    """
    # Check if running on Vercel
    if os.getenv('VERCEL_ENV'):
        # Production: Use Vercel's environment variables
        if os.getenv('VERCEL_ENV') == 'production':
            # Use production URL if available, fallback to deployment URL
            base_url = (f"https://{os.getenv('VERCEL_PROJECT_PRODUCTION_URL')}" 
                       if os.getenv('VERCEL_PROJECT_PRODUCTION_URL')
                       else f"https://{os.getenv('VERCEL_URL')}")
        else:
            # Preview/development on Vercel
            base_url = f"https://{os.getenv('VERCEL_URL')}"
            
        return {
            'frontend': base_url,
            'api': base_url,  # Same domain, different API routes
            'agent': base_url  # Now served as serverless functions
        }
    
    # Development: Use localhost with port offsets
    offset = int(os.getenv('SERVICE_PORT_OFFSET', '0'))
    
    return {
        'frontend': f"http://localhost:{3000 + offset}",
        'api': f"http://localhost:{8000 + offset}",
        'agent': f"http://localhost:{8001 + offset}"
    }


def get_agent_service_url() -> str:
    """Get the agent service URL for the current environment"""
    return get_service_urls()['agent']


def get_api_service_url() -> str:
    """Get the main API service URL for the current environment"""
    return get_service_urls()['api']


def get_frontend_url() -> str:
    """Get the frontend URL for the current environment"""
    return get_service_urls()['frontend']


def is_production() -> bool:
    """Check if running in production environment"""
    return os.getenv('VERCEL_ENV') == 'production'


def is_development() -> bool:
    """Check if running in development environment"""
    return not bool(os.getenv('VERCEL_ENV'))


def get_cors_origins() -> list:
    """Get allowed CORS origins for current environment"""
    if is_development():
        # Development: Allow multiple port offsets
        origins = []
        for offset in range(0, 31, 10):  # Support 0, 10, 20, 30 offsets
            origins.extend([
                f"http://localhost:{3000 + offset}",
                f"http://localhost:{8000 + offset}",
                f"http://localhost:{8001 + offset}"
            ])
        return origins
    else:
        # Production: Use current deployment URL
        urls = get_service_urls()
        return [urls['frontend']]