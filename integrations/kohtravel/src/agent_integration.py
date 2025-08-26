"""
KohTravel-specific agent integration
"""
import sys
import os
from typing import Dict, Any, Optional, List
import structlog
from datetime import datetime

# Add agent infrastructure to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../agent-infrastructure/src"))

from core.agent import Agent, AgentConfig
from providers.anthropic_provider import AnthropicProvider, AnthropicConfig
from tools.database import DocumentSearchTool, DatabaseQueryTool
from config.settings import get_settings, load_project_config

logger = structlog.get_logger(__name__)


class KohTravelAgentIntegration:
    """
    KohTravel-specific agent integration that connects the standalone agent
    infrastructure with KohTravel's specific requirements
    """
    
    def __init__(self, database_url: str, anthropic_api_key: str):
        self.database_url = database_url
        self.anthropic_api_key = anthropic_api_key
        self.agent: Optional[Agent] = None
        self.project_config = load_project_config("kohtravel")
        
    def initialize_agent(self) -> Agent:
        """Initialize KohTravel agent with project-specific configuration"""
        
        # Create Anthropic provider
        provider_config = AnthropicConfig(
            api_key=self.anthropic_api_key,
            model=self.project_config.get("provider", {}).get("model", "claude-3-5-sonnet-20241022")
        )
        provider = AnthropicProvider(provider_config)
        
        # Create agent configuration
        agent_config = AgentConfig(
            name=self.project_config.get("agent", {}).get("name", "KohTravel Travel Assistant"),
            system_prompt=self.project_config.get("agent", {}).get("system_prompt", "You are a travel assistant."),
            model=provider_config.model,
            temperature=self.project_config.get("provider", {}).get("temperature", 0.1),
            max_tokens=self.project_config.get("provider", {}).get("max_tokens", 4096),
            enabled_tools=self.project_config.get("tools", {}).get("enabled", [])
        )
        
        # Create agent
        self.agent = Agent(
            config=agent_config,
            provider=provider,
            tools={}
        )
        
        # Register context providers
        self.agent.register_context_provider(self.get_user_travel_context)
        
        # Register tools
        self._register_tools()
        
        logger.info("KohTravel agent initialized", tools=list(self.agent.tools.keys()))
        return self.agent
    
    def _register_tools(self):
        """Register KohTravel-specific tools"""
        
        # Document search tool with KohTravel customization
        doc_search_tool = DocumentSearchTool(self.database_url)
        self.agent.register_tool("search_documents", doc_search_tool)
        
        # Database query tool with allowed tables
        allowed_tables = self.project_config.get("tools", {}).get("configurations", {}).get("database_query", {}).get("allowed_tables", [])
        db_tool = DatabaseQueryTool(self.database_url, allowed_tables)
        self.agent.register_tool("database_query", db_tool)
        
        # Travel-specific tool
        travel_insights_tool = TravelInsightsTool(self.database_url)
        self.agent.register_tool("travel_insights", travel_insights_tool)
    
    async def get_user_travel_context(self, session_id: str, user_id: str = None, **kwargs) -> Dict[str, Any]:
        """
        Gather user's travel context for better agent responses
        """
        if not user_id:
            return {}
        
        try:
            # Get recent documents summary
            recent_docs = await self._get_recent_documents(user_id)
            
            # Get travel statistics
            travel_stats = await self._get_travel_statistics(user_id)
            
            # Get upcoming trips
            upcoming_trips = await self._get_upcoming_trips(user_id)
            
            context = {
                "user_profile": {
                    "user_id": user_id,
                    "total_documents": travel_stats.get("total_documents", 0),
                    "document_categories": travel_stats.get("categories", [])
                },
                "recent_documents": recent_docs,
                "travel_statistics": travel_stats,
                "upcoming_trips": upcoming_trips,
                "context_timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info("Travel context gathered", user_id=user_id, docs_count=len(recent_docs))
            return context
            
        except Exception as e:
            logger.error("Failed to gather travel context", user_id=user_id, error=str(e))
            return {"error": f"Context gathering failed: {str(e)}"}
    
    async def _get_recent_documents(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent documents for context"""
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        import sqlalchemy as sa
        
        engine = create_async_engine(self.database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        try:
            async with async_session() as session:
                query = """
                SELECT d.title, d.summary, dc.name as category, d.created_at
                FROM documents d
                LEFT JOIN document_categories dc ON d.category_id = dc.id
                WHERE d.user_id = :user_id
                ORDER BY d.created_at DESC
                LIMIT :limit
                """
                
                result = await session.execute(sa.text(query), {
                    "user_id": user_id,
                    "limit": limit
                })
                
                rows = result.fetchall()
                return [
                    {
                        "title": row[0],
                        "summary": row[1],
                        "category": row[2],
                        "created_at": row[3].isoformat() if row[3] else None
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error("Failed to get recent documents", error=str(e))
            return []
    
    async def _get_travel_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user's travel statistics"""
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        import sqlalchemy as sa
        
        engine = create_async_engine(self.database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        try:
            async with async_session() as session:
                # Get document counts by category
                query = """
                SELECT dc.name, COUNT(d.id) as count
                FROM documents d
                LEFT JOIN document_categories dc ON d.category_id = dc.id
                WHERE d.user_id = :user_id
                GROUP BY dc.name
                ORDER BY count DESC
                """
                
                result = await session.execute(sa.text(query), {"user_id": user_id})
                rows = result.fetchall()
                
                categories = [{"name": row[0], "count": row[1]} for row in rows]
                total_documents = sum(cat["count"] for cat in categories)
                
                return {
                    "total_documents": total_documents,
                    "categories": categories,
                    "most_common_category": categories[0]["name"] if categories else None
                }
                
        except Exception as e:
            logger.error("Failed to get travel statistics", error=str(e))
            return {"total_documents": 0, "categories": []}
    
    async def _get_upcoming_trips(self, user_id: str) -> List[Dict[str, Any]]:
        """Extract upcoming trip information from documents"""
        # This would analyze document structured_data for dates and locations
        # For now, return empty list
        return []


class TravelInsightsTool:
    """Custom tool for travel-specific insights"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.name = "travel_insights"
        self.description = "Get travel insights and patterns from user's documents"
    
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Provide travel insights"""
        user_id = context.get("user_id")
        if not user_id:
            return {"success": False, "error": "User ID required"}
        
        insight_type = parameters.get("type", "summary")
        
        if insight_type == "destinations":
            return await self._get_destination_insights(user_id)
        elif insight_type == "spending":
            return await self._get_spending_insights(user_id)
        else:
            return await self._get_general_insights(user_id)
    
    async def _get_destination_insights(self, user_id: str) -> Dict[str, Any]:
        """Analyze destinations from user's documents"""
        # This would parse structured_data for locations
        return {
            "success": True,
            "content": "Destination analysis not yet implemented",
            "metadata": {"insight_type": "destinations"}
        }
    
    async def _get_spending_insights(self, user_id: str) -> Dict[str, Any]:
        """Analyze spending patterns"""
        # This would parse structured_data for amounts and currencies
        return {
            "success": True,
            "content": "Spending analysis not yet implemented",
            "metadata": {"insight_type": "spending"}
        }
    
    async def _get_general_insights(self, user_id: str) -> Dict[str, Any]:
        """Provide general travel insights"""
        return {
            "success": True,
            "content": "You have travel documents organized across multiple categories. I can help you find specific information about your trips.",
            "metadata": {"insight_type": "general"}
        }