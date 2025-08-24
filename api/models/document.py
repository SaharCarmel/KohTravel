from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from database import Base

class DocumentCategory(Base):
    __tablename__ = "document_categories"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    keywords = Column(JSON, nullable=True)  # Array of keywords for classification
    extraction_fields = Column(JSON, nullable=True)  # Field definitions for extraction
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    documents = relationship("Document", back_populates="category")
    
    def __repr__(self):
        return f"<DocumentCategory(id={self.id}, name={self.name})>"

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("document_categories.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)
    file_hash = Column(String(64), nullable=True, index=True)  # SHA-256 hash for duplicate detection
    file_size = Column(Integer, nullable=True)  # File size in bytes
    raw_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    structured_data = Column(JSON, nullable=True)
    processing_status = Column(String(50), nullable=False, default='pending', index=True)
    confidence_score = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="documents")
    category = relationship("DocumentCategory", back_populates="documents")
    quick_refs = relationship("DocumentQuickRef", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(id={self.id}, title={self.title}, status={self.processing_status})>"

class DocumentQuickRef(Base):
    __tablename__ = "document_quick_refs"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    field_value = Column(Text, nullable=True)
    field_type = Column(String(50), nullable=True)  # 'date', 'currency', 'location', 'time'
    
    # Relationships
    document = relationship("Document", back_populates="quick_refs")
    
    def __repr__(self):
        return f"<DocumentQuickRef(field_name={self.field_name}, value={self.field_value})>"