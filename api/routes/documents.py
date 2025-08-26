from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from sse_starlette import EventSourceResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import uuid
import asyncio
import json
import hashlib
from io import BytesIO

from database import get_db
from models.user import User
from models.document import Document, DocumentCategory, DocumentQuickRef
from services.document_processor import DocumentProcessor
from services.auth import get_current_user

router = APIRouter()

# File upload validation
MAX_FILE_SIZE = 4.5 * 1024 * 1024  # 4.5MB
ALLOWED_EXTENSIONS = {".pdf"}

def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    # Check file extension
    if not any(file.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400, 
            detail="Only PDF files are allowed"
        )
    
    # Check file size (FastAPI doesn't provide size directly, we'll check in endpoint)
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE / (1024 * 1024):.1f}MB"
        )

@router.post("/upload")
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload one or more documents for processing"""
    
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > 10:  # Limit batch uploads
        raise HTTPException(status_code=400, detail="Maximum 10 files per upload")
    
    uploaded_documents = []
    processor = DocumentProcessor(db)
    
    for file in files:
        try:
            # Validate file
            validate_file(file)
            
            # Read file content
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} exceeds maximum size limit"
                )
            
            # Calculate file hash for duplicate detection
            file_hash = hashlib.sha256(content).hexdigest()
            
            # Check for duplicates
            existing_doc = db.query(Document).filter(
                Document.user_id == current_user.id,
                Document.file_hash == file_hash
            ).first()
            
            if existing_doc:
                uploaded_documents.append({
                    "id": str(existing_doc.id),
                    "filename": file.filename,
                    "status": "duplicate",
                    "message": f"File already exists (uploaded {existing_doc.created_at.strftime('%Y-%m-%d %H:%M')})",
                    "existing_document": {
                        "id": str(existing_doc.id),
                        "title": existing_doc.title,
                        "created_at": existing_doc.created_at.isoformat()
                    }
                })
                continue
            
            # Create document record
            document = Document(
                user_id=current_user.id,
                title=file.filename or "Untitled Document",
                original_filename=file.filename,
                file_hash=file_hash,
                file_size=len(content),
                processing_status="pending"
            )
            
            db.add(document)
            db.commit()
            db.refresh(document)
            
            # Schedule background processing
            background_tasks.add_task(
                processor.process_document_async,
                document.id,
                content
            )
            
            uploaded_documents.append({
                "id": str(document.id),
                "filename": file.filename,
                "status": "pending",
                "message": "Document uploaded successfully, processing started"
            })
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename}: {str(e)}")
    
    return {
        "uploaded_documents": uploaded_documents,
        "total_uploaded": len(uploaded_documents)
    }

@router.get("/")
async def get_documents(
    skip: int = 0,
    limit: int = 50,
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's documents with optional filtering"""
    
    query = db.query(Document).filter(Document.user_id == current_user.id)
    
    if category_id:
        query = query.filter(Document.category_id == category_id)
    
    if status:
        query = query.filter(Document.processing_status == status)
    
    # Order by creation date (newest first)
    query = query.order_by(Document.created_at.desc())
    
    # Apply pagination
    documents = query.offset(skip).limit(limit).all()
    
    # Get total count
    total = query.count()
    
    return {
        "documents": [
            {
                "id": str(doc.id),
                "title": doc.title,
                "original_filename": doc.original_filename,
                "category_id": doc.category_id,
                "processing_status": doc.processing_status,
                "confidence_score": doc.confidence_score,
                "created_at": doc.created_at,
                "updated_at": doc.updated_at,
                "summary": doc.summary[:200] + "..." if doc.summary and len(doc.summary) > 200 else doc.summary,
                "error_message": doc.error_message
            }
            for doc in documents
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific document by ID"""
    
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    
    document = db.query(Document).filter(
        Document.id == doc_uuid,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get quick reference fields
    quick_refs = db.query(DocumentQuickRef).filter(
        DocumentQuickRef.document_id == document.id
    ).all()
    
    return {
        "id": str(document.id),
        "title": document.title,
        "original_filename": document.original_filename,
        "category_id": document.category_id,
        "raw_text": document.raw_text,
        "summary": document.summary,
        "structured_data": document.structured_data,
        "processing_status": document.processing_status,
        "confidence_score": document.confidence_score,
        "error_message": document.error_message,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "quick_refs": [
            {
                "field_name": ref.field_name,
                "field_value": ref.field_value,
                "field_type": ref.field_type
            }
            for ref in quick_refs
        ]
    }

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a document"""
    
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    
    document = db.query(Document).filter(
        Document.id == doc_uuid,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully"}

@router.get("/{document_id}/processing-status")
async def get_processing_status(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get real-time processing status via Server-Sent Events"""
    
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    
    async def event_generator():
        while True:
            # Check document status in database
            document = db.query(Document).filter(
                Document.id == doc_uuid,
                Document.user_id == current_user.id
            ).first()
            
            if not document:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": "Document not found"})
                }
                return
            
            # Send status update
            yield {
                "event": "status",
                "data": json.dumps({
                    "document_id": str(document.id),
                    "status": document.processing_status,
                    "confidence_score": document.confidence_score,
                    "error_message": document.error_message,
                    "updated_at": document.updated_at.isoformat() if document.updated_at else None
                })
            }
            
            # If processing is complete or failed, stop streaming
            if document.processing_status in ["completed", "failed"]:
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "status": document.processing_status,
                        "final": True
                    })
                }
                return
            
            # Wait before next check
            await asyncio.sleep(2)
    
    return EventSourceResponse(event_generator())

@router.get("/categories/")
async def get_categories(db: Session = Depends(get_db)):
    """Get all document categories"""
    
    categories = db.query(DocumentCategory).all()
    
    return {
        "categories": [
            {
                "id": cat.id,
                "name": cat.name,
                "keywords": cat.keywords,
                "extraction_fields": cat.extraction_fields
            }
            for cat in categories
        ]
    }

@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reprocess an existing document with current AI model"""
    
    # Get the document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not document.raw_text:
        raise HTTPException(status_code=400, detail="Document raw text not available for reprocessing")
    
    # Reset processing fields
    document.processing_status = "processing"
    document.summary = None
    document.structured_data = None
    document.confidence_score = None
    document.error_message = None
    
    # Clear existing quick refs
    db.query(DocumentQuickRef).filter(DocumentQuickRef.document_id == document.id).delete()
    db.commit()
    
    # Schedule AI reprocessing with existing raw text
    async def reprocess_with_ai():
        try:
            processor = DocumentProcessor(db)
            if processor.claude_client:
                ai_result = await processor._process_with_ai(document.raw_text, document.original_filename)
                
                if ai_result and isinstance(ai_result, dict):
                    # Update document with AI results
                    document.summary = ai_result.get("summary")
                    document.structured_data = ai_result.get("structured_data")
                    document.confidence_score = ai_result.get("confidence_score")
                    
                    # Set category if identified
                    category_name = ai_result.get("category")
                    if category_name:
                        category = db.query(DocumentCategory).filter(
                            DocumentCategory.name.ilike(f"%{category_name}%")
                        ).first()
                        if category:
                            document.category_id = category.id
                    
                    # Create quick reference fields
                    quick_refs_data = ai_result.get("quick_refs", {})
                    if isinstance(quick_refs_data, dict):
                        for field_name, field_data in quick_refs_data.items():
                            if field_data is None or not isinstance(field_data, dict):
                                continue
                                
                            quick_ref = DocumentQuickRef(
                                document_id=document.id,
                                field_name=field_name,
                                field_value=str(field_data.get("value", "")),
                                field_type=field_data.get("type", "text")
                            )
                            db.add(quick_ref)
                
                # Mark as completed
                document.processing_status = "completed"
                db.commit()
            else:
                document.processing_status = "failed"
                document.error_message = "AI processing unavailable"
                db.commit()
                
        except Exception as e:
            document.processing_status = "failed"
            document.error_message = str(e)
            db.commit()
    
    background_tasks.add_task(reprocess_with_ai)
    
    return {
        "document_id": document_id,
        "status": "reprocessing_started",
        "message": "Document reprocessing started with current model configuration"
    }