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
                
                if ai_result and isinstance(ai_result, dict):
                    # Update document with AI results
                    document.summary = ai_result.get("summary")
                    document.structured_data = ai_result.get("structured_data")
                    document.confidence_score = ai_result.get("confidence_score")
                    
                    # Set category - create new one if needed
                    category_name = ai_result.get("category")
                    if category_name:
                        # First try to find existing category
                        category = self.db.query(DocumentCategory).filter(
                            DocumentCategory.name.ilike(f"%{category_name}%")
                        ).first()
                        
                        if not category:
                            # Create new category if it doesn't exist
                            category = DocumentCategory(name=category_name)
                            self.db.add(category)
                            self.db.flush()  # Get the ID
                            logger.info(f"Created new document category: {category_name}")
                        
                        document.category_id = category.id
                    
                    # Create quick reference fields
                    quick_refs_data = ai_result.get("quick_refs", {})
                    if isinstance(quick_refs_data, dict):
                        for field_name, field_data in quick_refs_data.items():
                            if field_data is None or not isinstance(field_data, dict):
                                logger.warning(f"Invalid field_data for {field_name}: {field_data}")
                                continue
                                
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
            
            # Call Claude API with configurable model
            model = os.getenv("DOCUMENT_PROCESSING_MODEL", "claude-3-haiku-20240307")
            message = self.claude_client.messages.create(
                model=model,
                max_tokens=4000,  # Higher token limit for detailed analysis
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
        """Create prompt for AI analysis with existing category intelligence"""
        
        # Get existing document categories
        existing_categories = self.db.query(DocumentCategory).all()
        categories_list = [cat.name for cat in existing_categories]
        
        filename_hint = f"Filename: {filename}\n\n" if filename else ""
        
        return f"""You are a travel document classification assistant. 

EXISTING DOCUMENT CATEGORIES:
{', '.join(categories_list)}

CLASSIFICATION TASK:
Analyze this document and decide whether to:
1. **Use an existing category** if the document clearly fits one of the above types
2. **Create a new category** if this document represents a new type of travel document

{filename_hint}Document Content:
{text}

Please analyze this document and respond with a JSON object containing:

1. "category": Choose from existing categories OR create a new descriptive category name (e.g., "Legal Policy", "Terms and Conditions", "Activity Voucher", "Insurance Policy")

2. "summary": A comprehensive summary that includes ALL travel segments, dates, destinations, and key details found in the document. For multi-segment trips, list each leg clearly.

3. "confidence_score": Float between 0-1 indicating confidence in the analysis

4. "structured_data": Object with ALL extracted information including:
   - all_flights: Array of flight objects with departure/arrival cities, dates, times, flight numbers
   - all_hotels: Array of hotel bookings with dates, locations
   - traveler_name: Passenger/guest name
   - booking_reference: Confirmation numbers
   - total_cost: Total price if available
   - travel_dates: Start and end dates of entire trip
   - destinations: All cities/countries visited
   - airlines: All carriers used

5. "quick_refs": Object with the most important searchable fields:
   - "total_amount": {{"value": "amount", "type": "currency"}}
   - "travel_period": {{"value": "start_date to end_date", "type": "date_range"}}
   - "destinations": {{"value": "City1, City2, City3", "type": "location"}}
   - "confirmation": {{"value": "booking_reference", "type": "text"}}
   - "passenger": {{"value": "traveler_name", "type": "text"}}

CRITICAL: Process the ENTIRE document. Do not truncate or ignore later sections. For multi-segment trips, capture ALL segments in your analysis.

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