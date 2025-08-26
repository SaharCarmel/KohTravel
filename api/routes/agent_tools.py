"""
Agent tools endpoints for KohTravel-specific functionality
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import structlog

from database import get_db
from models.document import Document, DocumentCategory, DocumentQuickRef
from models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter()


class ToolRequest(BaseModel):
    user_id: str
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
        
        if not query:
            return ToolResponse(
                success=False,
                content="Search query is required",
                error="missing_query"
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
            Document.user_id == request.user_id
        ).filter(
            # Search in multiple fields
            Document.raw_text.ilike(f"%{query}%") |
            Document.title.ilike(f"%{query}%") |
            Document.summary.ilike(f"%{query}%")
        )
        
        # Filter by category if specified
        if category:
            db_query = db_query.filter(DocumentCategory.name.ilike(f"%{category}%"))
        
        # Execute query
        results = db_query.order_by(Document.created_at.desc()).limit(limit).all()
        
        # Format results
        documents = []
        for result in results:
            doc = {
                "id": str(result.id),
                "title": result.title,
                "filename": result.original_filename,
                "summary": result.summary,
                "category": result.category,
                "created_at": result.created_at.isoformat() if result.created_at else None,
                "structured_data": result.structured_data or {}
            }
            documents.append(doc)
        
        return ToolResponse(
            success=True,
            content=f"Found {len(documents)} documents matching '{query}'" + 
                   (f" in category '{category}'" if category else ""),
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
        
        # Get document only if it belongs to the user
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == request.user_id
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
        
        return ToolResponse(
            success=True,
            content=f"Retrieved document: {document.title}",
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
        # Get document count by category
        category_stats = db.query(
            DocumentCategory.name,
            db.func.count(Document.id).label("count")
        ).join(
            Document, Document.category_id == DocumentCategory.id
        ).filter(
            Document.user_id == request.user_id
        ).group_by(DocumentCategory.name).all()
        
        # Get total documents
        total_docs = db.query(Document).filter(
            Document.user_id == request.user_id
        ).count()
        
        # Get recent documents
        recent_docs = db.query(
            Document.title,
            Document.created_at,
            DocumentCategory.name.label("category")
        ).join(
            DocumentCategory, Document.category_id == DocumentCategory.id, isouter=True
        ).filter(
            Document.user_id == request.user_id
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
        }
    ]
    
    return tools


@router.get("/system_prompt")
async def get_system_prompt():
    """
    Get KohTravel-specific system prompt for the agent
    """
    prompt = """You are a helpful travel assistant for KohTravel users. You help users understand and organize their travel documents.

You have access to the user's uploaded travel documents including:
- Flight tickets and boarding passes
- Hotel reservations and booking confirmations
- Restaurant reservations
- Tourist attraction tickets
- Travel insurance documents
- Visa and passport information

When users ask questions about their trips, always:
1. Use search_documents to find relevant information in their documents
2. Provide specific information from their documents with document references
3. Use get_document to get full details when needed
4. Use travel_summary to understand their overall travel portfolio
5. Offer helpful travel tips and suggestions based on their documents

Key capabilities:
- Search documents by content, title, or category
- Get detailed document information including structured data
- Provide travel statistics and summaries
- Help organize and understand travel information

Always be conversational, helpful, and accurate. Cite the specific documents you're referencing.
When you find relevant information, always mention which document it came from."""

    return {"system_prompt": prompt}