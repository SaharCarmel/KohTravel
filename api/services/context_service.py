"""
Context service for providing agent with current date/time and trip summary
"""
from datetime import datetime
from typing import Dict, Any
import pytz
from sqlalchemy.orm import Session

from models.user import User
from models.document import Document, DocumentCategory
from models.calendar_event import CalendarEvent
from services.user_migration import UserMigrationService


class TravelContextService:
    """Service for generating travel-specific context for the agent"""
    
    @staticmethod
    def get_current_datetime() -> str:
        """Get current date and time in a readable format"""
        now = datetime.now(pytz.UTC)
        formatted = now.strftime("%A, %B %d, %Y at %I:%M %p UTC")
        return f"Today is {formatted}"
    
    @staticmethod
    async def get_trip_summary(user_id: str, db: Session) -> str:
        """Generate a concise trip summary for the user"""
        try:
            # Get user with proper migration handling
            user_uuid = await UserMigrationService.get_accessible_user_id(user_id, db)
            if not user_uuid:
                return "No user data available"
            
            # Get document count by category
            from sqlalchemy import func
            category_stats = db.query(
                DocumentCategory.name,
                func.count(Document.id).label("count")
            ).join(
                Document, Document.category_id == DocumentCategory.id
            ).filter(
                Document.user_id == user_uuid
            ).group_by(DocumentCategory.name).all()
            
            # Get upcoming events (next 30 days)
            from datetime import timedelta
            future_cutoff = datetime.now(pytz.UTC) + timedelta(days=30)
            upcoming_events = db.query(CalendarEvent).filter(
                CalendarEvent.user_id == user_uuid,
                CalendarEvent.start_datetime >= datetime.now(pytz.UTC),
                CalendarEvent.start_datetime <= future_cutoff,
                CalendarEvent.status.in_(["confirmed", "tentative"])
            ).order_by(CalendarEvent.start_datetime).limit(5).all()
            
            # Build summary
            total_docs = sum(cat.count for cat in category_stats)
            
            summary_parts = [
                f"User has {total_docs} travel documents"
            ]
            
            if category_stats:
                categories = [f"{cat.name} ({cat.count})" for cat in category_stats if cat.count > 0]
                if categories:
                    summary_parts.append(f"Categories: {', '.join(categories)}")
            
            if upcoming_events:
                event_summary = []
                for event in upcoming_events:
                    date_str = event.start_datetime.strftime("%b %d")
                    event_summary.append(f"{event.title} ({date_str})")
                
                summary_parts.append(f"Upcoming events: {', '.join(event_summary)}")
            else:
                summary_parts.append("No upcoming events scheduled")
                
            return ". ".join(summary_parts) + "."
            
        except Exception as e:
            return f"Unable to generate trip summary: {str(e)}"
    
    @staticmethod
    async def get_agent_context(user_id: str, db: Session) -> Dict[str, Any]:
        """Get complete context for agent conversations"""
        return {
            "currentDateTime": TravelContextService.get_current_datetime(),
            "projectSummary": await TravelContextService.get_trip_summary(user_id, db)
        }