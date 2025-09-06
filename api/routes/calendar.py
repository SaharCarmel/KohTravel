from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, date, timedelta
import uuid

from database import get_db
from models.calendar_event import CalendarEvent
from models.user import User
from services.auth import get_current_user
from pydantic import BaseModel, Field

# Pydantic models for request/response
class CalendarEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    location: Optional[str] = None
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    all_day: bool = False
    event_type: str = Field(..., pattern="^(flight|accommodation|activity|transport|dining|wellness)$")
    color: Optional[str] = None
    status: str = Field(default="confirmed", pattern="^(confirmed|tentative|cancelled|suggested)$")
    notes: Optional[str] = None
    document_id: Optional[str] = None
    suggestion_reason: Optional[str] = None
    suggestion_confidence: Optional[int] = Field(None, ge=1, le=10)
    suggested_by: Optional[str] = None

class CalendarEventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    location: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    all_day: Optional[bool] = None
    event_type: Optional[str] = Field(None, pattern="^(flight|accommodation|activity|transport|dining|wellness)$")
    color: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(confirmed|tentative|cancelled|suggested)$")
    notes: Optional[str] = None

class SuggestedEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    location: Optional[str] = None
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    all_day: bool = False
    event_type: str = Field(..., pattern="^(flight|accommodation|activity|transport|dining|wellness)$")
    color: Optional[str] = None
    notes: Optional[str] = None
    document_id: Optional[str] = None
    suggestion_reason: str = Field(..., min_length=1)
    suggestion_confidence: int = Field(..., ge=1, le=10)
    suggested_by: str = Field(default="agent")

class EventApprovalRequest(BaseModel):
    approved: bool
    user_feedback: Optional[str] = None

class CalendarEventResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    location: Optional[str]
    start_datetime: datetime
    end_datetime: Optional[datetime]
    all_day: bool
    event_type: str
    color: Optional[str]
    status: str
    notes: Optional[str]
    source: str
    document_id: Optional[str]
    suggestion_reason: Optional[str]
    suggestion_confidence: Optional[int]
    user_feedback: Optional[str]
    suggested_by: Optional[str]
    parent_event_id: Optional[str]
    created_at: datetime
    updated_at: datetime

router = APIRouter(
    prefix="/api/calendar",
    tags=["calendar"]
)

@router.get("/events", response_model=List[CalendarEventResponse])
async def get_events(
    start_date: Optional[date] = Query(None, description="Filter events from this date"),
    end_date: Optional[date] = Query(None, description="Filter events until this date"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get calendar events for the authenticated user"""
    
    query = db.query(CalendarEvent).filter(CalendarEvent.user_id == current_user.id)
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(CalendarEvent.start_datetime >= start_date)
    if end_date:
        # Add one day to include events on the end_date
        end_datetime = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1)
        query = query.filter(CalendarEvent.start_datetime < end_datetime)
    
    # Apply event type filter if provided
    if event_type:
        query = query.filter(CalendarEvent.event_type == event_type)
    
    # Order by start datetime
    events = query.order_by(CalendarEvent.start_datetime).all()
    
    return [CalendarEventResponse(**event.to_dict()) for event in events]

@router.get("/events/suggested", response_model=List[CalendarEventResponse])
async def get_suggested_events(
    limit: Optional[int] = Query(None, description="Limit number of suggestions returned"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all pending suggested events for the authenticated user"""
    
    query = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == current_user.id,
        CalendarEvent.status == "suggested"
    ).order_by(CalendarEvent.start_datetime)
    
    if limit:
        query = query.limit(limit)
    
    events = query.all()
    return [CalendarEventResponse(**event.to_dict()) for event in events]

@router.get("/events/{event_id}", response_model=CalendarEventResponse)
async def get_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific calendar event"""
    
    try:
        event_uuid = uuid.UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event ID format")
    
    event = db.query(CalendarEvent).filter(
        CalendarEvent.id == event_uuid,
        CalendarEvent.user_id == current_user.id
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return CalendarEventResponse(**event.to_dict())

@router.post("/events", response_model=CalendarEventResponse)
async def create_event(
    event_data: CalendarEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new calendar event"""
    
    # Validate document_id if provided
    document_uuid = None
    if event_data.document_id:
        try:
            document_uuid = uuid.UUID(event_data.document_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document ID format")
    
    # Set default color based on event type if not provided
    color_map = {
        "flight": "bg-blue-500",
        "accommodation": "bg-green-500",
        "activity": "bg-purple-500",
        "transport": "bg-cyan-500",
        "dining": "bg-yellow-500",
        "wellness": "bg-pink-500"
    }
    
    if not event_data.color:
        event_data.color = color_map.get(event_data.event_type, "bg-gray-500")
    
    # Create the event
    event = CalendarEvent(
        user_id=current_user.id,
        title=event_data.title,
        description=event_data.description,
        location=event_data.location,
        start_datetime=event_data.start_datetime,
        end_datetime=event_data.end_datetime,
        all_day=event_data.all_day,
        event_type=event_data.event_type,
        color=event_data.color,
        status=event_data.status,
        notes=event_data.notes,
        document_id=document_uuid,
        source="manual",
        suggestion_reason=getattr(event_data, 'suggestion_reason', None),
        suggestion_confidence=getattr(event_data, 'suggestion_confidence', None),
        suggested_by=getattr(event_data, 'suggested_by', None)
    )
    
    db.add(event)
    db.commit()
    db.refresh(event)
    
    return CalendarEventResponse(**event.to_dict())

@router.put("/events/{event_id}", response_model=CalendarEventResponse)
async def update_event(
    event_id: str,
    event_data: CalendarEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a calendar event"""
    
    try:
        event_uuid = uuid.UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event ID format")
    
    event = db.query(CalendarEvent).filter(
        CalendarEvent.id == event_uuid,
        CalendarEvent.user_id == current_user.id
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Update fields that are provided
    update_data = event_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    db.commit()
    db.refresh(event)
    
    return CalendarEventResponse(**event.to_dict())

@router.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a calendar event"""
    
    try:
        event_uuid = uuid.UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event ID format")
    
    event = db.query(CalendarEvent).filter(
        CalendarEvent.id == event_uuid,
        CalendarEvent.user_id == current_user.id
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    db.delete(event)
    db.commit()
    
    return JSONResponse(content={"message": "Event deleted successfully"})

@router.get("/event-types")
async def get_event_types():
    """Get available event types and their colors"""
    event_types = [
        {"type": "flight", "label": "Flight", "color": "bg-blue-500"},
        {"type": "accommodation", "label": "Accommodation", "color": "bg-green-500"},
        {"type": "activity", "label": "Activity", "color": "bg-purple-500"},
        {"type": "transport", "label": "Transport", "color": "bg-cyan-500"},
        {"type": "dining", "label": "Dining", "color": "bg-yellow-500"},
        {"type": "wellness", "label": "Wellness", "color": "bg-pink-500"}
    ]
    return {"event_types": event_types}

@router.get("/stats")
async def get_calendar_stats(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get calendar statistics for the user"""
    
    query = db.query(CalendarEvent).filter(CalendarEvent.user_id == current_user.id)
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(CalendarEvent.start_datetime >= start_date)
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1)
        query = query.filter(CalendarEvent.start_datetime < end_datetime)
    
    # Get total count
    total_events = query.count()
    
    # Get count by event type
    event_type_counts = (
        query.with_entities(CalendarEvent.event_type, func.count(CalendarEvent.id))
        .group_by(CalendarEvent.event_type)
        .all()
    )
    
    return {
        "total_events": total_events,
        "events_by_type": {event_type: count for event_type, count in event_type_counts},
        "date_range": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None
        }
    }

# Suggested Events Endpoints

@router.post("/events/suggest", response_model=CalendarEventResponse)
async def create_suggested_event(
    event_data: SuggestedEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a suggested calendar event (typically called by agent)"""
    
    # Validate document_id if provided
    document_uuid = None
    if event_data.document_id:
        try:
            document_uuid = uuid.UUID(event_data.document_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document ID format")
    
    # Set default color based on event type if not provided
    color_map = {
        "flight": "bg-blue-500",
        "accommodation": "bg-green-500", 
        "activity": "bg-purple-500",
        "transport": "bg-cyan-500",
        "dining": "bg-yellow-500",
        "wellness": "bg-pink-500"
    }
    
    if not event_data.color:
        event_data.color = color_map.get(event_data.event_type, "bg-gray-500")
    
    # Create the suggested event
    event = CalendarEvent(
        user_id=current_user.id,
        title=event_data.title,
        description=event_data.description,
        location=event_data.location,
        start_datetime=event_data.start_datetime,
        end_datetime=event_data.end_datetime,
        all_day=event_data.all_day,
        event_type=event_data.event_type,
        color=event_data.color,
        status="suggested",  # Always suggested for this endpoint
        notes=event_data.notes,
        document_id=document_uuid,
        source="agent",
        suggestion_reason=event_data.suggestion_reason,
        suggestion_confidence=event_data.suggestion_confidence,
        suggested_by=event_data.suggested_by
    )
    
    db.add(event)
    db.commit()
    db.refresh(event)
    
    return CalendarEventResponse(**event.to_dict())


@router.post("/events/{event_id}/approve", response_model=CalendarEventResponse)
async def approve_suggested_event(
    event_id: str,
    approval_data: EventApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve or reject a suggested event"""
    
    try:
        event_uuid = uuid.UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event ID format")
    
    event = db.query(CalendarEvent).filter(
        CalendarEvent.id == event_uuid,
        CalendarEvent.user_id == current_user.id,
        CalendarEvent.status == "suggested"
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Suggested event not found")
    
    if approval_data.approved:
        # Create a new confirmed event based on the suggestion
        approved_event = CalendarEvent(
            user_id=current_user.id,
            title=event.title,
            description=event.description,
            location=event.location,
            start_datetime=event.start_datetime,
            end_datetime=event.end_datetime,
            all_day=event.all_day,
            event_type=event.event_type,
            color=event.color,
            status="confirmed",
            notes=event.notes,
            document_id=event.document_id,
            source="approved_suggestion",
            parent_event_id=event.id
        )
        
        db.add(approved_event)
        
        # Keep the original suggested event for reference but mark it as processed
        event.user_feedback = approval_data.user_feedback or "Approved"
        
        db.commit()
        db.refresh(approved_event)
        
        return CalendarEventResponse(**approved_event.to_dict())
    else:
        # Reject the suggestion
        event.user_feedback = approval_data.user_feedback or "Rejected"
        event.status = "cancelled"  # Mark as cancelled to hide from suggested events
        
        db.commit()
        db.refresh(event)
        
        return CalendarEventResponse(**event.to_dict())

@router.delete("/events/{event_id}/suggestion")
async def delete_suggested_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a suggested event completely"""
    
    try:
        event_uuid = uuid.UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event ID format")
    
    event = db.query(CalendarEvent).filter(
        CalendarEvent.id == event_uuid,
        CalendarEvent.user_id == current_user.id,
        CalendarEvent.status == "suggested"
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Suggested event not found")
    
    db.delete(event)
    db.commit()
    
    return JSONResponse(content={"message": "Suggested event deleted successfully"})