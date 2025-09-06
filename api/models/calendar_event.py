from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from database import Base

class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Basic event information
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)
    
    # Event timing
    start_datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    end_datetime = Column(DateTime(timezone=True), nullable=True, index=True)
    all_day = Column(Boolean, default=False)
    
    # Event categorization
    event_type = Column(String(50), nullable=False, index=True)  # flight, accommodation, activity, transport, dining, wellness
    color = Column(String(20), nullable=True)  # CSS color class like 'bg-blue-500'
    
    # Event source and references
    source = Column(String(50), default='manual')  # manual, document_extracted, imported
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True, index=True)
    external_id = Column(String(255), nullable=True, index=True)  # For future integrations
    
    # Status and metadata
    status = Column(String(20), default='confirmed')  # confirmed, tentative, cancelled, suggested
    notes = Column(Text, nullable=True)
    
    # Suggested events metadata
    suggestion_reason = Column(Text, nullable=True)  # AI reasoning for the suggestion
    suggestion_confidence = Column(Integer, nullable=True)  # 1-10 confidence score
    user_feedback = Column(Text, nullable=True)  # User's rejection reason
    suggested_by = Column(String(100), nullable=True)  # 'agent', 'user', etc.
    parent_event_id = Column(UUID(as_uuid=True), ForeignKey("calendar_events.id"), nullable=True, index=True)  # Links approved event to original suggestion
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="calendar_events")
    document = relationship("Document", backref="calendar_events")
    
    # Self-referential relationship for suggested events
    parent_event = relationship("CalendarEvent", remote_side=[id], backref="suggested_events")
    
    def __repr__(self):
        return f"<CalendarEvent(id={self.id}, title={self.title}, type={self.event_type}, start={self.start_datetime})>"

    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "start_datetime": self.start_datetime.isoformat() if self.start_datetime else None,
            "end_datetime": self.end_datetime.isoformat() if self.end_datetime else None,
            "all_day": self.all_day,
            "event_type": self.event_type,
            "color": self.color,
            "status": self.status,
            "notes": self.notes,
            "source": self.source,
            "document_id": str(self.document_id) if self.document_id else None,
            "suggestion_reason": self.suggestion_reason,
            "suggestion_confidence": self.suggestion_confidence,
            "user_feedback": self.user_feedback,
            "suggested_by": self.suggested_by,
            "parent_event_id": str(self.parent_event_id) if self.parent_event_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }