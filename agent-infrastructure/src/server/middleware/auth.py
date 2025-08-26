"""
Authentication middleware
"""
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import Response
import structlog

logger = structlog.get_logger(__name__)


class AuthMiddleware:
    """Basic authentication middleware"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Skip auth for health endpoints
        if request.url.path.startswith("/health"):
            await self.app(scope, receive, send)
            return
        
        # Check authentication
        if not await self._is_authenticated(request):
            response = Response(
                content='{"detail": "Authentication required"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"Content-Type": "application/json"}
            )
            await response(scope, receive, send)
            return
        
        await self.app(scope, receive, send)
    
    async def _is_authenticated(self, request: Request) -> bool:
        """Check if request is authenticated"""
        # Check for API key in header
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            # Check for Bearer token
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                api_key = auth_header.split(" ")[1]
        
        if not api_key:
            logger.warning("No API key provided", path=request.url.path)
            return False
        
        # Validate API key (in production, use proper validation)
        # For now, just check if it's not empty
        return len(api_key.strip()) > 0
    
    async def _extract_user_info(self, request: Request) -> Optional[dict]:
        """Extract user information from request"""
        # In production, decode JWT or validate API key
        # For now, return basic info
        api_key = request.headers.get("X-API-Key") or ""
        
        if not api_key:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                api_key = auth_header.split(" ")[1]
        
        if api_key:
            return {
                "api_key": api_key[:8] + "..." if len(api_key) > 8 else api_key,
                "authenticated": True
            }
        
        return None