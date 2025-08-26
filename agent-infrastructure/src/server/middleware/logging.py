"""
Logging middleware
"""
import time
from typing import Callable
from fastapi import Request, Response
import structlog

logger = structlog.get_logger(__name__)


class LoggingMiddleware:
    """Request logging middleware"""
    
    def __init__(self, app: Callable):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        start_time = time.time()
        
        # Capture response info
        response_info = {"status_code": None, "content_length": None}
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                response_info["status_code"] = message["status"]
                response_info["headers"] = message.get("headers", [])
            elif message["type"] == "http.response.body":
                if "body" in message:
                    response_info["content_length"] = len(message["body"])
            await send(message)
        
        # Process request
        await self.app(scope, receive, send_wrapper)
        
        # Log request completion
        process_time = time.time() - start_time
        
        # Extract relevant headers
        user_agent = request.headers.get("user-agent", "")
        x_forwarded_for = request.headers.get("x-forwarded-for", "")
        
        logger.info(
            "Request completed",
            method=request.method,
            url=str(request.url),
            status_code=response_info["status_code"],
            process_time=process_time,
            content_length=response_info["content_length"],
            user_agent=user_agent,
            x_forwarded_for=x_forwarded_for,
            client_host=request.client.host if request.client else None
        )