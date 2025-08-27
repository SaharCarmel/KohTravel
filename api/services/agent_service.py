"""
Agent service for KohTravel - handles agent initialization with prompts
"""
import httpx
from typing import Optional, Dict, Any
import structlog

from utils.prompt_loader import prompt_loader

logger = structlog.get_logger(__name__)


class KohTravelAgentService:
    """Service for managing KohTravel agents with proper prompt injection"""
    
    def __init__(self, agent_infrastructure_url: str = "http://localhost:8001"):
        self.agent_infrastructure_url = agent_infrastructure_url
        self.agent_name = "travel-assistant"
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for KohTravel travel assistant"""
        prompt = prompt_loader.load_agent_prompt(self.agent_name)
        
        if prompt is None:
            logger.warning("Failed to load travel assistant prompt, using fallback")
            # Fallback prompt
            prompt = """You are a helpful travel assistant for KohTravel users. 
            You help users understand and organize their travel documents."""
        else:
            # Log that we loaded the prompt and show a sample to verify content
            logger.info("Agent prompt loaded successfully", 
                       agent=self.agent_name,
                       prompt_length=len(prompt),
                       contains_workflow=("tool_workflow" in prompt),
                       contains_step_1=("step_1" in prompt),
                       sample=prompt[:200] + "..." if len(prompt) > 200 else prompt)
        
        return prompt
    
    def get_tool_prompts(self) -> Dict[str, str]:
        """Get all tool prompts/documentation"""
        return prompt_loader.get_all_tool_prompts()
    
    async def initialize_agent(self, user_id: str) -> bool:
        """Initialize agent with KohTravel-specific configuration for a user"""
        try:
            system_prompt = self.get_system_prompt()
            
            # Send initialization request to agent infrastructure
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.agent_infrastructure_url}/api/agent/init",
                    json={
                        "project": "kohtravel",
                        "system_prompt": system_prompt,
                        "session_id": f"kohtravel-{user_id}",  # User-specific session
                        "user_id": user_id
                    }
                )
                response.raise_for_status()
                
                logger.info("Agent initialized successfully for user", user_id=user_id)
                return True
                
        except Exception as e:
            logger.error("Failed to initialize agent", user_id=user_id, error=str(e))
            return False
    
    async def send_message(
        self, 
        session_id: str, 
        message: str, 
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send message to agent with KohTravel context"""
        try:
            # Always ensure agent has latest prompts by reinitializing
            await self.initialize_agent(user_id)
            
            async with httpx.AsyncClient(timeout=60) as client:
                payload = {
                    "session_id": session_id,
                    "message": message,
                    "project": "kohtravel",
                    "user_id": user_id,
                    "context": context or {}
                }
                
                response = await client.post(
                    f"{self.agent_infrastructure_url}/api/agent/chat",
                    json=payload
                )
                response.raise_for_status()
                
                return response.json()
                
        except Exception as e:
            logger.error("Failed to send message to agent", 
                        session_id=session_id, error=str(e))
            raise


# Global service instance
kohtravel_agent_service = KohTravelAgentService()