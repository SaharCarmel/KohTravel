"""
Agent tools endpoints for KohTravel-specific functionality
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import String
import structlog

from database import get_db
from models.document import Document, DocumentCategory, DocumentQuickRef
from models.user import User
from models.calendar_event import CalendarEvent
import uuid
from datetime import datetime, date

logger = structlog.get_logger(__name__)

router = APIRouter()


class ToolRequest(BaseModel):
    user_id: str  # This will be email from the agent
    parameters: Dict[str, Any]




class ToolResponse(BaseModel):
    success: bool
    content: str
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None


@router.post("/search_documents", response_model=ToolResponse)
async def search_user_documents(request: ToolRequest, db: Session = Depends(get_db)):
    """
    Search through user's uploaded documents
    Only returns documents belonging to the authenticated user
    """
    try:
        query = request.parameters.get("query", "")
        category = request.parameters.get("category")
        limit = min(request.parameters.get("limit", 10), 50)  # Cap at 50
        
        # Log the exact query being searched
        logger.info("Search query received", 
                   query=query, 
                   query_length=len(query),
                   category=category,
                   user_id=request.user_id)
        
        if not query:
            return ToolResponse(
                success=False,
                content="Search query is required",
                error="missing_query"
            )
        
        # Get user with proper migration handling
        from services.user_migration import UserMigrationService
        user_uuid = await UserMigrationService.get_accessible_user_id(request.user_id, db)
        if not user_uuid:
            return ToolResponse(
                success=False,
                content="User authentication failed",
                error="auth_failed"
            )
        
        # Build query for user's documents only
        db_query = db.query(
            Document.id,
            Document.title,
            Document.original_filename,
            Document.summary,
            Document.structured_data,
            Document.created_at,
            DocumentCategory.name.label("category")
        ).join(
            DocumentCategory, Document.category_id == DocumentCategory.id, isouter=True
        ).filter(
            Document.user_id == user_uuid
        ).filter(
            # Search in multiple fields including structured data
            Document.raw_text.ilike(f"%{query}%") |
            Document.title.ilike(f"%{query}%") |
            Document.summary.ilike(f"%{query}%") |
            Document.structured_data.cast(String).ilike(f"%{query}%")
        )
        
        # Filter by category if specified
        if category:
            db_query = db_query.filter(DocumentCategory.name.ilike(f"%{category}%"))
        
        # Execute query
        results = db_query.order_by(Document.created_at.desc()).limit(limit).all()
        
        # Log query results for debugging
        logger.info("Search query executed", 
                   query=query,
                   results_found=len(results),
                   result_titles=[r.title for r in results[:3]])  # Log first 3 titles
        
        # Format results with document references
        documents = []
        for idx, result in enumerate(results):
            doc = {
                "id": str(result.id),
                "ref": f"doc_{idx + 1}",  # Simple reference for LLM
                "title": result.title,
                "filename": result.original_filename,
                "summary": result.summary,
                "category": result.category,
                "created_at": result.created_at.isoformat() if result.created_at else None,
                "structured_data": result.structured_data or {}
            }
            documents.append(doc)
        
        # Debug logging
        logger.info("Search documents result", 
                   document_count=len(documents), 
                   sample_ids=[doc["id"] for doc in documents[:3]])
        
        # Create more informative content for the agent
        if documents:
            doc_list = []
            for doc in documents:
                doc_summary = f"- {doc['ref']} ({doc['id']}): {doc['title']}"
                if doc.get('summary'):
                    # Show first 100 chars of summary
                    summary_preview = doc['summary'][:100] + "..." if len(doc['summary']) > 100 else doc['summary']
                    doc_summary += f" - {summary_preview}"
                doc_list.append(doc_summary)
            
            content = f"Found {len(documents)} documents matching '{query}'" + \
                     (f" in category '{category}'" if category else "") + \
                     f":\n\n" + "\n".join(doc_list) + \
                     f"\n\nUse get_document with the ref (like '{documents[0]['ref']}') or ID to get full details."
        else:
            content = f"No documents found matching '{query}'" + \
                     (f" in category '{category}'" if category else "")
        
        return ToolResponse(
            success=True,
            content=content,
            metadata={
                "documents": documents,
                "count": len(documents),
                "search_query": query,
                "category_filter": category
            }
        )
        
    except Exception as e:
        logger.error("Document search failed", error=str(e), user_id=request.user_id)
        return ToolResponse(
            success=False,
            content=f"Document search failed: {str(e)}",
            error=str(e)
        )


@router.post("/get_document", response_model=ToolResponse)
async def get_user_document(request: ToolRequest, db: Session = Depends(get_db)):
    """
    Get specific document by ID (user-scoped)
    """
    try:
        document_id = request.parameters.get("document_id")
        
        if not document_id:
            return ToolResponse(
                success=False,
                content="Document ID is required",
                error="missing_document_id"
            )
        
        # Debug logging
        logger.info("Get document request", 
                   document_id=document_id, 
                   user_id=request.user_id)
        
        # Get user with proper migration handling
        from services.user_migration import UserMigrationService
        user_uuid = await UserMigrationService.get_accessible_user_id(request.user_id, db)
        if not user_uuid:
            return ToolResponse(
                success=False,
                content="User authentication failed",
                error="auth_failed"
            )
        
        # Handle both ref format (doc_1) and UUID format
        if isinstance(document_id, str) and document_id.startswith("doc_"):
            # This is a reference format, need to resolve to actual UUID
            # Get recent search results to map ref to UUID
            try:
                ref_num = int(document_id.replace("doc_", ""))
                
                # Get user documents to find the one at this index
                db_query = db.query(Document).filter(
                    Document.user_id == user_uuid
                ).order_by(Document.created_at.desc())
                
                # Get the document at the specified index (1-based)
                target_document = db_query.offset(ref_num - 1).limit(1).first()
                
                if not target_document:
                    return ToolResponse(
                        success=False,
                        content=f"Document reference {document_id} not found",
                        error="document_ref_not_found"
                    )
                
                document_id = target_document.id
                
            except (ValueError, IndexError):
                return ToolResponse(
                    success=False,
                    content=f"Invalid document reference format: {document_id}",
                    error="invalid_ref_format"
                )
        else:
            # Convert document_id to UUID if it's a string UUID
            try:
                if isinstance(document_id, str):
                    document_id = uuid.UUID(document_id)
            except ValueError:
                return ToolResponse(
                    success=False,
                    content=f"Invalid document ID format: {document_id}",
                    error="invalid_uuid"
                )
        
        # Get document only if it belongs to the user
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_uuid
        ).first()
        
        if not document:
            return ToolResponse(
                success=False,
                content=f"Document not found or access denied",
                error="document_not_found"
            )
        
        # Get category
        category = db.query(DocumentCategory).filter(
            DocumentCategory.id == document.category_id
        ).first()
        
        doc_data = {
            "id": str(document.id),
            "title": document.title,
            "filename": document.original_filename,
            "summary": document.summary,
            "content": document.raw_text,
            "category": category.name if category else None,
            "structured_data": document.structured_data or {},
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "processing_status": document.processing_status,
            "confidence_score": document.confidence_score
        }
        
        # Debug logging
        logger.info("Document retrieved successfully", 
                   document_id=str(document.id),
                   title=document.title,
                   content_length=len(document.raw_text or ""),
                   summary_length=len(document.summary or ""))
        
        # Give the agent complete raw text so it can find whatever it needs
        primary_content = f"Document: {document.title}\n\n"
        primary_content += f"Summary: {document.summary}\n\n"
        primary_content += f"Full Document Content:\n{document.raw_text}"
        
        return ToolResponse(
            success=True,
            content=primary_content,
            metadata={"document": doc_data}
        )
        
    except Exception as e:
        logger.error("Get document failed", error=str(e), user_id=request.user_id)
        return ToolResponse(
            success=False,
            content=f"Failed to get document: {str(e)}",
            error=str(e)
        )


@router.post("/travel_summary", response_model=ToolResponse)
async def get_travel_summary(request: ToolRequest, db: Session = Depends(get_db)):
    """
    Get user's travel summary and statistics
    """
    try:
        # Get user with proper migration handling
        from services.user_migration import UserMigrationService
        user_uuid = await UserMigrationService.get_accessible_user_id(request.user_id, db)
        if not user_uuid:
            return ToolResponse(
                success=False,
                content="User authentication failed",
                error="auth_failed"
            )
        
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
        
        # Get total documents
        total_docs = db.query(Document).filter(
            Document.user_id == user_uuid
        ).count()
        
        # Get recent documents
        recent_docs = db.query(
            Document.title,
            Document.created_at,
            DocumentCategory.name.label("category")
        ).join(
            DocumentCategory, Document.category_id == DocumentCategory.id, isouter=True
        ).filter(
            Document.user_id == user_uuid
        ).order_by(Document.created_at.desc()).limit(5).all()
        
        # Format data
        categories = [{"name": cat.name, "count": cat.count} for cat in category_stats]
        recent = [
            {
                "title": doc.title,
                "category": doc.category,
                "uploaded": doc.created_at.isoformat() if doc.created_at else None
            }
            for doc in recent_docs
        ]
        
        summary = f"You have {total_docs} travel documents across {len(categories)} categories."
        if categories:
            most_common = max(categories, key=lambda x: x["count"])
            summary += f" Most documents are in '{most_common['name']}' category ({most_common['count']} documents)."
        
        return ToolResponse(
            success=True,
            content=summary,
            metadata={
                "total_documents": total_docs,
                "categories": categories,
                "recent_documents": recent,
                "summary_stats": {
                    "most_common_category": categories[0]["name"] if categories else None,
                    "has_documents": total_docs > 0
                }
            }
        )
        
    except Exception as e:
        logger.error("Travel summary failed", error=str(e), user_id=request.user_id)
        return ToolResponse(
            success=False,
            content=f"Failed to get travel summary: {str(e)}",
            error=str(e)
        )


@router.post("/get_document_categories", response_model=ToolResponse)
async def get_document_categories(request: ToolRequest, db: Session = Depends(get_db)):
    """
    Get all available document categories to guide search strategy
    """
    try:
        # Get user with proper migration handling
        from services.user_migration import UserMigrationService
        user_uuid = await UserMigrationService.get_accessible_user_id(request.user_id, db)
        if not user_uuid:
            return ToolResponse(
                success=False,
                content="User authentication failed",
                error="auth_failed"
            )
        
        # Get categories with document counts for this user
        from sqlalchemy import func
        categories = db.query(
            DocumentCategory.name,
            func.count(Document.id).label("count")
        ).outerjoin(
            Document, (Document.category_id == DocumentCategory.id) & (Document.user_id == user_uuid)
        ).group_by(DocumentCategory.name).all()
        
        # Format response
        category_list = []
        for cat in categories:
            if cat.count > 0:  # Only show categories with documents
                category_list.append(f"{cat.name} ({cat.count} documents)")
        
        content = f"Available document categories:\n" + "\n".join([f"- {cat}" for cat in category_list])
        content += f"\n\nUse these categories to filter searches with category parameter."
        
        return ToolResponse(
            success=True,
            content=content,
            metadata={"categories": [{"name": cat.name, "count": cat.count} for cat in categories]}
        )
        
    except Exception as e:
        logger.error("Get categories failed", error=str(e), user_id=request.user_id)
        return ToolResponse(
            success=False,
            content=f"Failed to get categories: {str(e)}",
            error=str(e)
        )


@router.post("/get_calendar_events", response_model=ToolResponse)
async def get_user_calendar_events(request: ToolRequest, db: Session = Depends(get_db)):
    """
    Get user's calendar events for travel planning
    """
    try:
        # Get user with proper migration handling
        from services.user_migration import UserMigrationService
        user_uuid = await UserMigrationService.get_accessible_user_id(request.user_id, db)
        if not user_uuid:
            return ToolResponse(
                success=False,
                content="User authentication failed",
                error="auth_failed"
            )
        
        # Parse parameters
        start_date = request.parameters.get("start_date")
        end_date = request.parameters.get("end_date")
        event_type = request.parameters.get("event_type")
        limit = min(request.parameters.get("limit", 50), 100)  # Cap at 100
        
        # Build query
        query = db.query(CalendarEvent).filter(CalendarEvent.user_id == user_uuid)
        
        # Apply filters
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(CalendarEvent.start_datetime >= start_dt)
            except ValueError:
                return ToolResponse(
                    success=False,
                    content=f"Invalid start_date format: {start_date}. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
                    error="invalid_date_format"
                )
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(CalendarEvent.start_datetime <= end_dt)
            except ValueError:
                return ToolResponse(
                    success=False,
                    content=f"Invalid end_date format: {end_date}. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
                    error="invalid_date_format"
                )
        
        if event_type:
            query = query.filter(CalendarEvent.event_type == event_type)
        
        # Execute query
        events = query.order_by(CalendarEvent.start_datetime).limit(limit).all()
        
        # Format events for response
        event_list = []
        for event in events:
            event_data = {
                "id": str(event.id),
                "title": event.title,
                "description": event.description,
                "location": event.location,
                "start_datetime": event.start_datetime.isoformat(),
                "end_datetime": event.end_datetime.isoformat() if event.end_datetime else None,
                "event_type": event.event_type,
                "status": event.status,
                "all_day": event.all_day
            }
            event_list.append(event_data)
        
        # Create readable content
        if event_list:
            content_lines = [f"Found {len(event_list)} calendar events:"]
            for event in event_list:
                event_line = f"- {event['title']} ({event['event_type']}) on {event['start_datetime'][:10]}"
                if event['location']:
                    event_line += f" at {event['location']}"
                content_lines.append(event_line)
            content = "\n".join(content_lines)
        else:
            filters_desc = ""
            if start_date or end_date:
                filters_desc += f" between {start_date or 'beginning'} and {end_date or 'end'}"
            if event_type:
                filters_desc += f" of type '{event_type}'"
            content = f"No calendar events found{filters_desc}."
        
        logger.info("Calendar events retrieved", 
                   user_id=request.user_id,
                   event_count=len(event_list),
                   start_date=start_date,
                   end_date=end_date,
                   event_type=event_type)
        
        return ToolResponse(
            success=True,
            content=content,
            metadata={
                "events": event_list,
                "count": len(event_list),
                "filters": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "event_type": event_type
                }
            }
        )
        
    except Exception as e:
        logger.error("Get calendar events failed", error=str(e), user_id=request.user_id)
        return ToolResponse(
            success=False,
            content=f"Failed to get calendar events: {str(e)}",
            error=str(e)
        )


@router.post("/create_calendar_event", response_model=ToolResponse)
async def create_user_calendar_event(request: ToolRequest, db: Session = Depends(get_db)):
    """
    Create a new calendar event for the user
    """
    try:
        # Get user with proper migration handling
        from services.user_migration import UserMigrationService
        user_uuid = await UserMigrationService.get_accessible_user_id(request.user_id, db)
        if not user_uuid:
            return ToolResponse(
                success=False,
                content="User authentication failed",
                error="auth_failed"
            )
        
        # Extract required parameters
        title = request.parameters.get("title")
        start_datetime = request.parameters.get("start_datetime")
        event_type = request.parameters.get("event_type", "activity")
        
        if not title:
            return ToolResponse(
                success=False,
                content="Event title is required",
                error="missing_title"
            )
        
        if not start_datetime:
            return ToolResponse(
                success=False,
                content="Event start_datetime is required",
                error="missing_start_datetime"
            )
        
        # Validate event type
        valid_types = ["flight", "accommodation", "activity", "transport", "dining", "wellness"]
        if event_type not in valid_types:
            return ToolResponse(
                success=False,
                content=f"Invalid event_type '{event_type}'. Must be one of: {', '.join(valid_types)}",
                error="invalid_event_type"
            )
        
        # Parse datetime
        try:
            start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
        except ValueError:
            return ToolResponse(
                success=False,
                content=f"Invalid start_datetime format: {start_datetime}. Use ISO format (YYYY-MM-DDTHH:MM:SS)",
                error="invalid_datetime_format"
            )
        
        # Parse end_datetime if provided
        end_dt = None
        end_datetime = request.parameters.get("end_datetime")
        if end_datetime:
            try:
                end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
            except ValueError:
                return ToolResponse(
                    success=False,
                    content=f"Invalid end_datetime format: {end_datetime}. Use ISO format (YYYY-MM-DDTHH:MM:SS)",
                    error="invalid_datetime_format"
                )
        
        # Set default color based on event type
        color_map = {
            "flight": "bg-blue-500",
            "accommodation": "bg-green-500",
            "activity": "bg-purple-500",
            "transport": "bg-cyan-500",
            "dining": "bg-yellow-500",
            "wellness": "bg-pink-500"
        }
        
        # Create the event
        new_event = CalendarEvent(
            user_id=user_uuid,
            title=title,
            description=request.parameters.get("description"),
            location=request.parameters.get("location"),
            start_datetime=start_dt,
            end_datetime=end_dt,
            all_day=request.parameters.get("all_day", False),
            event_type=event_type,
            color=request.parameters.get("color", color_map.get(event_type, "bg-gray-500")),
            status=request.parameters.get("status", "confirmed"),
            notes=request.parameters.get("notes"),
            source="agent_created"
        )
        
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        
        # Format response
        event_data = new_event.to_dict()
        content = f"Calendar event '{title}' created successfully for {start_dt.strftime('%Y-%m-%d %H:%M')}"
        if new_event.location:
            content += f" at {new_event.location}"
        content += f". Event ID: {event_data['id']}"
        
        logger.info("Calendar event created", 
                   user_id=request.user_id,
                   event_id=event_data["id"],
                   title=title,
                   event_type=event_type)
        
        return ToolResponse(
            success=True,
            content=content,
            metadata={"event": event_data}
        )
        
    except Exception as e:
        logger.error("Create calendar event failed", error=str(e), user_id=request.user_id)
        return ToolResponse(
            success=False,
            content=f"Failed to create calendar event: {str(e)}",
            error=str(e)
        )


@router.post("/update_calendar_event", response_model=ToolResponse)
async def update_user_calendar_event(request: ToolRequest, db: Session = Depends(get_db)):
    """
    Update an existing calendar event
    """
    try:
        # Get user with proper migration handling
        from services.user_migration import UserMigrationService
        user_uuid = await UserMigrationService.get_accessible_user_id(request.user_id, db)
        if not user_uuid:
            return ToolResponse(
                success=False,
                content="User authentication failed",
                error="auth_failed"
            )
        
        event_id = request.parameters.get("event_id")
        if not event_id:
            return ToolResponse(
                success=False,
                content="Event ID is required",
                error="missing_event_id"
            )
        
        # Parse event ID
        try:
            event_uuid = uuid.UUID(event_id)
        except ValueError:
            return ToolResponse(
                success=False,
                content=f"Invalid event ID format: {event_id}",
                error="invalid_event_id"
            )
        
        # Get the event (user-scoped)
        event = db.query(CalendarEvent).filter(
            CalendarEvent.id == event_uuid,
            CalendarEvent.user_id == user_uuid
        ).first()
        
        if not event:
            return ToolResponse(
                success=False,
                content=f"Calendar event not found or access denied",
                error="event_not_found"
            )
        
        # Update fields if provided
        updates = {}
        for field in ["title", "description", "location", "event_type", "status", "notes", "all_day"]:
            if field in request.parameters:
                updates[field] = request.parameters[field]
        
        # Handle datetime updates
        if "start_datetime" in request.parameters:
            try:
                start_dt = datetime.fromisoformat(request.parameters["start_datetime"].replace('Z', '+00:00'))
                updates["start_datetime"] = start_dt
            except ValueError:
                return ToolResponse(
                    success=False,
                    content=f"Invalid start_datetime format: {request.parameters['start_datetime']}",
                    error="invalid_datetime_format"
                )
        
        if "end_datetime" in request.parameters:
            if request.parameters["end_datetime"]:
                try:
                    end_dt = datetime.fromisoformat(request.parameters["end_datetime"].replace('Z', '+00:00'))
                    updates["end_datetime"] = end_dt
                except ValueError:
                    return ToolResponse(
                        success=False,
                        content=f"Invalid end_datetime format: {request.parameters['end_datetime']}",
                        error="invalid_datetime_format"
                    )
            else:
                updates["end_datetime"] = None
        
        # Apply updates
        for field, value in updates.items():
            setattr(event, field, value)
        
        db.commit()
        db.refresh(event)
        
        # Format response
        event_data = event.to_dict()
        content = f"Calendar event '{event.title}' updated successfully. Event ID: {event_data['id']}"
        
        logger.info("Calendar event updated", 
                   user_id=request.user_id,
                   event_id=event_data["id"],
                   updates=list(updates.keys()))
        
        return ToolResponse(
            success=True,
            content=content,
            metadata={"event": event_data, "updated_fields": list(updates.keys())}
        )
        
    except Exception as e:
        logger.error("Update calendar event failed", error=str(e), user_id=request.user_id)
        return ToolResponse(
            success=False,
            content=f"Failed to update calendar event: {str(e)}",
            error=str(e)
        )


@router.post("/delete_calendar_event", response_model=ToolResponse)
async def delete_user_calendar_event(request: ToolRequest, db: Session = Depends(get_db)):
    """
    Delete a calendar event
    """
    try:
        # Get user with proper migration handling
        from services.user_migration import UserMigrationService
        user_uuid = await UserMigrationService.get_accessible_user_id(request.user_id, db)
        if not user_uuid:
            return ToolResponse(
                success=False,
                content="User authentication failed",
                error="auth_failed"
            )
        
        event_id = request.parameters.get("event_id")
        if not event_id:
            return ToolResponse(
                success=False,
                content="Event ID is required",
                error="missing_event_id"
            )
        
        # Parse event ID
        try:
            event_uuid = uuid.UUID(event_id)
        except ValueError:
            return ToolResponse(
                success=False,
                content=f"Invalid event ID format: {event_id}",
                error="invalid_event_id"
            )
        
        # Get the event (user-scoped)
        event = db.query(CalendarEvent).filter(
            CalendarEvent.id == event_uuid,
            CalendarEvent.user_id == user_uuid
        ).first()
        
        if not event:
            return ToolResponse(
                success=False,
                content=f"Calendar event not found or access denied",
                error="event_not_found"
            )
        
        event_title = event.title
        event_id_str = str(event.id)
        
        # Delete the event
        db.delete(event)
        db.commit()
        
        content = f"Calendar event '{event_title}' deleted successfully."
        
        logger.info("Calendar event deleted", 
                   user_id=request.user_id,
                   event_id=event_id_str,
                   title=event_title)
        
        return ToolResponse(
            success=True,
            content=content,
            metadata={"deleted_event_id": event_id_str, "deleted_title": event_title}
        )
        
    except Exception as e:
        logger.error("Delete calendar event failed", error=str(e), user_id=request.user_id)
        return ToolResponse(
            success=False,
            content=f"Failed to delete calendar event: {str(e)}",
            error=str(e)
        )


@router.post("/suggest_calendar_event", response_model=ToolResponse)
async def suggest_user_calendar_event(request: ToolRequest, db: Session = Depends(get_db)):
    """
    Suggest a new calendar event for the user's review and approval
    This creates a suggested event that appears in the chat carousel and calendar with special styling
    """
    try:
        # Get user with proper migration handling
        from services.user_migration import UserMigrationService
        user_uuid = await UserMigrationService.get_accessible_user_id(request.user_id, db)
        if not user_uuid:
            return ToolResponse(
                success=False,
                content="User authentication failed",
                error="auth_failed"
            )
        
        # Extract required parameters
        title = request.parameters.get("title")
        start_datetime = request.parameters.get("start_datetime")
        event_type = request.parameters.get("event_type", "activity")
        suggestion_reason = request.parameters.get("suggestion_reason")
        suggestion_confidence = request.parameters.get("suggestion_confidence", 7)
        
        if not title:
            return ToolResponse(
                success=False,
                content="Event title is required",
                error="missing_title"
            )
        
        if not start_datetime:
            return ToolResponse(
                success=False,
                content="Event start_datetime is required",
                error="missing_start_datetime"
            )
            
        if not suggestion_reason:
            return ToolResponse(
                success=False,
                content="Suggestion reason is required for suggested events",
                error="missing_suggestion_reason"
            )
        
        # Validate event type
        valid_types = ["flight", "accommodation", "activity", "transport", "dining", "wellness"]
        if event_type not in valid_types:
            return ToolResponse(
                success=False,
                content=f"Invalid event_type '{event_type}'. Must be one of: {', '.join(valid_types)}",
                error="invalid_event_type"
            )
        
        # Validate confidence score
        if not isinstance(suggestion_confidence, int) or not (1 <= suggestion_confidence <= 10):
            return ToolResponse(
                success=False,
                content="Suggestion confidence must be an integer between 1 and 10",
                error="invalid_confidence"
            )
        
        # Parse datetime
        try:
            start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
        except ValueError:
            return ToolResponse(
                success=False,
                content=f"Invalid start_datetime format: {start_datetime}. Use ISO format (YYYY-MM-DDTHH:MM:SS)",
                error="invalid_datetime_format"
            )
        
        # Parse end_datetime if provided
        end_dt = None
        end_datetime = request.parameters.get("end_datetime")
        if end_datetime:
            try:
                end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
            except ValueError:
                return ToolResponse(
                    success=False,
                    content=f"Invalid end_datetime format: {end_datetime}. Use ISO format (YYYY-MM-DDTHH:MM:SS)",
                    error="invalid_datetime_format"
                )
        
        # Set default color based on event type
        color_map = {
            "flight": "bg-blue-500",
            "accommodation": "bg-green-500",
            "activity": "bg-purple-500", 
            "transport": "bg-cyan-500",
            "dining": "bg-yellow-500",
            "wellness": "bg-pink-500"
        }
        
        # Create the suggested event
        suggested_event = CalendarEvent(
            user_id=user_uuid,
            title=title,
            description=request.parameters.get("description"),
            location=request.parameters.get("location"),
            start_datetime=start_dt,
            end_datetime=end_dt,
            all_day=request.parameters.get("all_day", False),
            event_type=event_type,
            color=request.parameters.get("color", color_map.get(event_type, "bg-gray-500")),
            status="suggested",  # Always suggested for this endpoint
            notes=request.parameters.get("notes"),
            source="agent_suggested",
            suggestion_reason=suggestion_reason,
            suggestion_confidence=suggestion_confidence,
            suggested_by="agent"
        )
        
        db.add(suggested_event)
        db.commit()
        db.refresh(suggested_event)
        
        # Format response
        event_data = suggested_event.to_dict()
        content = f"I've suggested a calendar event '{title}' for {start_dt.strftime('%Y-%m-%d %H:%M')}"
        if suggested_event.location:
            content += f" at {suggested_event.location}"
        content += f". You can review and approve this suggestion in the chat interface or calendar view."
        content += f"\n\nReason: {suggestion_reason}"
        content += f"\nConfidence: {suggestion_confidence}/10"
        
        logger.info("Calendar event suggested", 
                   user_id=request.user_id,
                   event_id=event_data["id"],
                   title=title,
                   event_type=event_type,
                   confidence=suggestion_confidence)
        
        return ToolResponse(
            success=True,
            content=content,
            metadata={"suggested_event": event_data}
        )
        
    except Exception as e:
        logger.error("Suggest calendar event failed", error=str(e), user_id=request.user_id)
        return ToolResponse(
            success=False,
            content=f"Failed to suggest calendar event: {str(e)}",
            error=str(e)
        )


@router.post("/show_suggested_events_carousel", response_model=ToolResponse)
async def show_suggested_events_carousel(request: ToolRequest, db: Session = Depends(get_db)):
    """
    Signal the frontend to show the suggested events carousel
    Use this after creating event suggestions to prompt user for approval
    """
    try:
        # Get user with proper migration handling
        from services.user_migration import UserMigrationService
        user_uuid = await UserMigrationService.get_accessible_user_id(request.user_id, db)
        if not user_uuid:
            return ToolResponse(
                success=False,
                content="User authentication failed",
                error="auth_failed"
            )
        
        # Get current suggested events count
        suggested_count = db.query(CalendarEvent).filter(
            CalendarEvent.user_id == user_uuid,
            CalendarEvent.status == "suggested"
        ).count()
        
        content = f"Showing suggested events carousel with {suggested_count} suggestions for your review."
        if suggested_count == 0:
            content = "No suggested events to display. Create some suggestions first using suggest_calendar_event."
        
        logger.info("Showing suggested events carousel", 
                   user_id=request.user_id,
                   suggested_count=suggested_count)
        
        return ToolResponse(
            success=True,
            content=content,
            metadata={
                "action": "show_carousel",
                "suggested_count": suggested_count
            }
        )
        
    except Exception as e:
        logger.error("Show carousel failed", error=str(e), user_id=request.user_id)
        return ToolResponse(
            success=False,
            content=f"Failed to show carousel: {str(e)}",
            error=str(e)
        )


@router.get("/available_tools", response_model=List[Dict[str, Any]])
async def get_available_tools():
    """
    Get list of available KohTravel-specific tools for the agent
    """
    tools = [
        {
            "name": "search_documents",
            "description": "Search through user's uploaded travel documents by content or title",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for document content"
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by document category (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of documents to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_document",
            "description": "Get detailed information about a specific document by ID",
            "parameters": {
                "type": "object", 
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "ID of the document to retrieve"
                    }
                },
                "required": ["document_id"]
            }
        },
        {
            "name": "travel_summary",
            "description": "Get user's travel document summary and statistics",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_document_categories",
            "description": "Get all available document categories to understand what types of documents exist",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_calendar_events",
            "description": "Get user's calendar events for travel planning, with optional date and type filtering",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Filter events from this date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Filter events until this date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                    },
                    "event_type": {
                        "type": "string",
                        "description": "Filter by event type: flight, accommodation, activity, transport, dining, wellness"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of events to return (default: 50, max: 100)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "create_calendar_event",
            "description": "Create a new calendar event for travel planning",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Event title"
                    },
                    "start_datetime": {
                        "type": "string",
                        "description": "Event start date and time (ISO format: YYYY-MM-DDTHH:MM:SS)"
                    },
                    "end_datetime": {
                        "type": "string",
                        "description": "Event end date and time (optional, ISO format: YYYY-MM-DDTHH:MM:SS)"
                    },
                    "event_type": {
                        "type": "string",
                        "description": "Event type: flight, accommodation, activity, transport, dining, wellness (default: activity)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description (optional)"
                    },
                    "location": {
                        "type": "string",
                        "description": "Event location (optional)"
                    },
                    "all_day": {
                        "type": "boolean",
                        "description": "Whether this is an all-day event (default: false)"
                    },
                    "status": {
                        "type": "string",
                        "description": "Event status: confirmed, tentative, cancelled (default: confirmed)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes (optional)"
                    }
                },
                "required": ["title", "start_datetime"]
            }
        },
        {
            "name": "update_calendar_event",
            "description": "Update an existing calendar event",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "ID of the event to update"
                    },
                    "title": {
                        "type": "string",
                        "description": "Event title (optional)"
                    },
                    "start_datetime": {
                        "type": "string",
                        "description": "Event start date and time (optional, ISO format: YYYY-MM-DDTHH:MM:SS)"
                    },
                    "end_datetime": {
                        "type": "string",
                        "description": "Event end date and time (optional, ISO format: YYYY-MM-DDTHH:MM:SS)"
                    },
                    "event_type": {
                        "type": "string",
                        "description": "Event type: flight, accommodation, activity, transport, dining, wellness (optional)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description (optional)"
                    },
                    "location": {
                        "type": "string",
                        "description": "Event location (optional)"
                    },
                    "all_day": {
                        "type": "boolean",
                        "description": "Whether this is an all-day event (optional)"
                    },
                    "status": {
                        "type": "string",
                        "description": "Event status: confirmed, tentative, cancelled (optional)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes (optional)"
                    }
                },
                "required": ["event_id"]
            }
        },
        {
            "name": "delete_calendar_event",
            "description": "Delete a calendar event",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "ID of the event to delete"
                    }
                },
                "required": ["event_id"]
            }
        },
        {
            "name": "suggest_calendar_event",
            "description": "Suggest a new calendar event that appears in the chat carousel for user approval. Use this when you want to propose events based on user documents or conversation context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Event title"
                    },
                    "start_datetime": {
                        "type": "string",
                        "description": "Event start date and time (ISO format: YYYY-MM-DDTHH:MM:SS)"
                    },
                    "end_datetime": {
                        "type": "string",
                        "description": "Event end date and time (optional, ISO format: YYYY-MM-DDTHH:MM:SS)"
                    },
                    "event_type": {
                        "type": "string",
                        "description": "Event type: flight, accommodation, activity, transport, dining, wellness (default: activity)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description (optional)"
                    },
                    "location": {
                        "type": "string",
                        "description": "Event location (optional)"
                    },
                    "all_day": {
                        "type": "boolean",
                        "description": "Whether this is an all-day event (default: false)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes (optional)"
                    },
                    "suggestion_reason": {
                        "type": "string",
                        "description": "Required: Explain why you're suggesting this event to help the user understand the recommendation"
                    },
                    "suggestion_confidence": {
                        "type": "integer",
                        "description": "Confidence level from 1-10 for this suggestion (default: 7)"
                    }
                },
                "required": ["title", "start_datetime", "suggestion_reason"]
            }
        },
        {
            "name": "show_suggested_events_carousel",
            "description": "Display the suggested events carousel in the chat interface. Use this after creating event suggestions to prompt the user for approval/rejection.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    ]
    
    return tools


