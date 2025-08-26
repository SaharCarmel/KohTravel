"""
Client for communicating with the agent infrastructure service
"""
import httpx
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)


class AgentClient:
    """
    Client for communicating with the standalone agent infrastructure
    """
    
    def __init__(self, base_url: str = "http://localhost:8001", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
        
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        return headers
    
    async def send_message(
        self,
        session_id: str,
        message: str,
        user_id: Optional[str] = None,
        project: str = "kohtravel",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message to the agent and get complete response
        """
        try:
            payload = {
                "session_id": session_id,
                "message": message,
                "project": project,
                "user_id": user_id,
                "context": context or {}
            }
            
            response = await self.client.post(
                f"{self.base_url}/agent/chat",
                json=payload,
                headers=self._get_headers()
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info("Message sent successfully", session_id=session_id, status=result.get("status"))
            return result
            
        except httpx.HTTPError as e:
            logger.error("HTTP error sending message", error=str(e), session_id=session_id)
            return {
                "session_id": session_id,
                "status": "error",
                "message": f"HTTP error: {str(e)}"
            }
        except Exception as e:
            logger.error("Error sending message", error=str(e), session_id=session_id)
            return {
                "session_id": session_id,
                "status": "error", 
                "message": f"Client error: {str(e)}"
            }
    
    async def stream_message(
        self,
        session_id: str,
        message: str,
        user_id: Optional[str] = None,
        project: str = "kohtravel",
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Send a message to the agent and stream response
        """
        try:
            payload = {
                "session_id": session_id,
                "message": message,
                "project": project,
                "user_id": user_id,
                "context": context or {}
            }
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/agent/chat/stream",
                json=payload,
                headers=self._get_headers()
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            import json
                            data = json.loads(line[6:])  # Remove "data: " prefix
                            yield data
                        except json.JSONDecodeError:
                            continue
                
        except httpx.HTTPError as e:
            logger.error("HTTP error streaming message", error=str(e), session_id=session_id)
            yield {
                "type": "error",
                "data": {"error": f"HTTP error: {str(e)}"},
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error("Error streaming message", error=str(e), session_id=session_id)
            yield {
                "type": "error",
                "data": {"error": f"Client error: {str(e)}"},
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_conversation(self, session_id: str, project: str = "kohtravel") -> Dict[str, Any]:
        """Get conversation history"""
        try:
            response = await self.client.get(
                f"{self.base_url}/agent/conversation/{session_id}",
                params={"project": project},
                headers=self._get_headers()
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error("Error getting conversation", error=str(e), session_id=session_id)
            return {
                "session_id": session_id,
                "project": project,
                "messages": [],
                "error": str(e)
            }
    
    async def clear_conversation(self, session_id: str, project: str = "kohtravel") -> Dict[str, Any]:
        """Clear conversation history"""
        try:
            response = await self.client.delete(
                f"{self.base_url}/agent/conversation/{session_id}",
                params={"project": project},
                headers=self._get_headers()
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error("Error clearing conversation", error=str(e), session_id=session_id)
            return {
                "session_id": session_id,
                "project": project,
                "status": "error",
                "error": str(e)
            }
    
    async def list_tools(self, project: str = "kohtravel") -> Dict[str, Any]:
        """Get available tools for project"""
        try:
            response = await self.client.get(
                f"{self.base_url}/agent/tools",
                params={"project": project},
                headers=self._get_headers()
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error("Error listing tools", error=str(e), project=project)
            return {
                "project": project,
                "tools": [],
                "error": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check agent service health"""
        try:
            response = await self.client.get(f"{self.base_url}/health/")
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Convenience functions for KohTravel integration
async def send_travel_query(
    message: str,
    user_id: str,
    session_id: Optional[str] = None,
    agent_url: str = "http://localhost:8001"
) -> Dict[str, Any]:
    """Send a travel-related query to the agent"""
    
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
    
    async with AgentClient(agent_url) as client:
        return await client.send_message(
            session_id=session_id,
            message=message,
            user_id=user_id,
            project="kohtravel"
        )


async def stream_travel_query(
    message: str,
    user_id: str,
    session_id: Optional[str] = None,
    agent_url: str = "http://localhost:8001"
) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream a travel-related query to the agent"""
    
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
    
    async with AgentClient(agent_url) as client:
        async for chunk in client.stream_message(
            session_id=session_id,
            message=message,
            user_id=user_id,
            project="kohtravel"
        ):
            yield chunk