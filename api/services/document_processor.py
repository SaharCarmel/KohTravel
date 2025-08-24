import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
from io import BytesIO
import tempfile
import os

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from sqlalchemy.orm import Session
import anthropic

from models.document import Document, DocumentCategory, DocumentQuickRef

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, db: Session):
        self.db = db
        self.converter = DocumentConverter()
        
        # Initialize Claude client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not found. AI features will be disabled.")
            self.claude_client = None
        else:
            self.claude_client = anthropic.Anthropic(api_key=api_key)
    
    async def process_document_async(self, document_id: str, file_content: bytes):
        """Process document asynchronously"""
        try:
            # Update status to processing
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.error(f"Document {document_id} not found")
                return
            
            document.processing_status = "processing"
            self.db.commit()
            
            # Extract text using Docling
            logger.info(f"Extracting text from document {document_id}")
            raw_text = await self._extract_text(file_content, document.original_filename)
            
            if not raw_text:
                raise Exception("Failed to extract text from document")
            
            document.raw_text = raw_text
            self.db.commit()
            
            # Process with Claude AI if available
            if self.claude_client:
                logger.info(f"Processing document {document_id} with AI")
                ai_result = await self._process_with_ai(raw_text, document.original_filename)
                
                if ai_result:
                    # Update document with AI results
                    document.summary = ai_result.get("summary")
                    document.structured_data = ai_result.get("structured_data")
                    document.confidence_score = ai_result.get("confidence_score")
                    
                    # Set category if identified
                    category_name = ai_result.get("category")
                    if category_name:
                        category = self.db.query(DocumentCategory).filter(
                            DocumentCategory.name.ilike(f"%{category_name}%")
                        ).first()
                        if category:
                            document.category_id = category.id
                    
                    # Create quick reference fields
                    quick_refs_data = ai_result.get("quick_refs", {})
                    for field_name, field_data in quick_refs_data.items():
                        quick_ref = DocumentQuickRef(
                            document_id=document.id,
                            field_name=field_name,
                            field_value=str(field_data.get("value", "")),
                            field_type=field_data.get("type", "text")
                        )
                        self.db.add(quick_ref)
            
            # Mark as completed
            document.processing_status = "completed"
            self.db.commit()
            
            logger.info(f"Document {document_id} processed successfully")
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            
            # Update document with error
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.processing_status = "failed"
                document.error_message = str(e)
                self.db.commit()
    
    async def _extract_text(self, file_content: bytes, filename: Optional[str] = None) -> str:
        """Extract text from PDF using Docling"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(file_content)
                temp_file.flush()
                
                try:
                    # Convert document
                    result = self.converter.convert(temp_file.name)
                    
                    # Extract markdown text
                    if result and result.document:
                        return result.document.export_to_markdown()
                    else:
                        logger.warning("No document content extracted")
                        return ""
                        
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            raise Exception(f"Text extraction failed: {str(e)}")
    
    async def _process_with_ai(self, raw_text: str, filename: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Process document with Claude AI"""
        if not self.claude_client:
            return None
        
        try:
            # Create AI prompt for document analysis
            prompt = self._create_analysis_prompt(raw_text, filename)
            
            # Call Claude API
            message = self.claude_client.messages.create(
                model="claude-3-haiku-20240307",  # Using Haiku for faster processing
                max_tokens=2000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Parse response
            response_text = message.content[0].text if message.content else ""
            
            # Extract JSON from response
            result = self._parse_ai_response(response_text)
            return result
            
        except Exception as e:
            logger.error(f"AI processing error: {str(e)}")
            return None
    
    def _create_analysis_prompt(self, text: str, filename: Optional[str] = None) -> str:
        """Create prompt for AI analysis"""
        
        filename_hint = f"Filename: {filename}\n\n" if filename else ""
        
        return f"""You are a travel document analysis assistant. Analyze this document and extract key information.

{filename_hint}Document Content:
{text[:4000]}...  # Truncate for token limits

Please analyze this document and respond with a JSON object containing:

1. "category": The document type (e.g., "flight_booking", "hotel_reservation", "restaurant_receipt", "tour_booking", "transport_ticket", "visa_document", "travel_insurance", "other")

2. "summary": A concise 2-3 sentence summary of the document

3. "confidence_score": Float between 0-1 indicating confidence in the analysis

4. "structured_data": Object with key document fields like:
   - dates (departure, arrival, booking date)
   - locations (cities, countries, addresses)
   - prices and currencies
   - confirmation numbers
   - traveler names
   - company/service provider

5. "quick_refs": Object with frequently searched fields:
   - "total_amount": {{"value": "123.45", "type": "currency"}}
   - "travel_date": {{"value": "2024-03-15", "type": "date"}}
   - "destination": {{"value": "Paris", "type": "location"}}
   - "confirmation": {{"value": "ABC123", "type": "text"}}

Focus on travel-related information. If this doesn't appear to be a travel document, set category to "other" and confidence_score below 0.5.

Respond with valid JSON only, no additional text."""
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response and extract JSON"""
        try:
            # Try to find JSON in response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                logger.warning("No valid JSON found in AI response")
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response JSON: {str(e)}")
            return {}
    
    def get_processing_status(self, document_id: str) -> Dict[str, Any]:
        """Get current processing status of a document"""
        document = self.db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            return {"error": "Document not found"}
        
        return {
            "document_id": str(document.id),
            "status": document.processing_status,
            "confidence_score": document.confidence_score,
            "error_message": document.error_message,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None
        }