"""
Agent cleanup and session management routes
"""
from typing import Dict, Any
from fastapi import APIRouter, BackgroundTasks
import structlog
from datetime import datetime, timedelta

from .agent import user_agents

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/cleanup/inactive")
async def cleanup_inactive_agents(background_tasks: BackgroundTasks):
    """Clean up agents that haven't been used recently"""
    
    def cleanup_task():
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=1)  # 1 hour timeout
            inactive_agents = []
            
            for agent_key, agent in list(user_agents.items()):
                # Check if agent has any recent activity
                has_recent_activity = False
                for conversation in agent.conversations.values():
                    if conversation.updated_at > cutoff_time:
                        has_recent_activity = True
                        break
                
                if not has_recent_activity:
                    inactive_agents.append(agent_key)
            
            # Remove inactive agents
            for agent_key in inactive_agents:
                del user_agents[agent_key]
                logger.info("Cleaned up inactive agent", agent_key=agent_key)
                
            logger.info("Agent cleanup completed", 
                       removed=len(inactive_agents), 
                       active=len(user_agents))
                       
        except Exception as e:
            logger.error("Agent cleanup failed", error=str(e))
    
    background_tasks.add_task(cleanup_task)
    return {"status": "cleanup_scheduled"}


@router.delete("/user/{user_id}/agents")
async def cleanup_user_agents(user_id: str):
    """Clean up all agents for a specific user"""
    try:
        removed_agents = []
        
        for agent_key in list(user_agents.keys()):
            if agent_key.endswith(f":{user_id}"):
                del user_agents[agent_key]
                removed_agents.append(agent_key)
        
        logger.info("User agents cleaned up", 
                   user_id=user_id, 
                   removed=len(removed_agents))
        
        return {
            "user_id": user_id,
            "removed_agents": removed_agents,
            "status": "cleaned"
        }
        
    except Exception as e:
        logger.error("User agent cleanup failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_agent_stats():
    """Get statistics about active agents and sessions"""
    try:
        total_agents = len(user_agents)
        total_conversations = sum(len(agent.conversations) for agent in user_agents.values())
        
        project_stats = {}
        user_stats = {}
        
        for agent_key, agent in user_agents.items():
            project, user_id = agent_key.split(":", 1)
            
            # Project stats
            if project not in project_stats:
                project_stats[project] = {"agents": 0, "conversations": 0}
            project_stats[project]["agents"] += 1
            project_stats[project]["conversations"] += len(agent.conversations)
            
            # User stats
            if user_id not in user_stats:
                user_stats[user_id] = {"agents": 0, "conversations": 0}
            user_stats[user_id]["agents"] += 1
            user_stats[user_id]["conversations"] += len(agent.conversations)
        
        return {
            "total_agents": total_agents,
            "total_conversations": total_conversations,
            "unique_users": len(user_stats),
            "unique_projects": len(project_stats),
            "project_breakdown": project_stats,
            "user_breakdown": user_stats
        }
        
    except Exception as e:
        logger.error("Failed to get agent stats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))