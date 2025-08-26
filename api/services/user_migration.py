"""
Production-grade user migration service for development phase
"""
from sqlalchemy.orm import Session
from typing import List, Optional
import structlog

from models.user import User
from models.document import Document

logger = structlog.get_logger(__name__)


class UserMigrationService:
    """
    Handles user migration and document access during development phase
    """
    
    @staticmethod
    async def get_accessible_user_id(email: str, db: Session) -> Optional[str]:
        """
        Get user ID with proper access logic for development phase
        
        Production logic:
        1. Find user by email
        2. If not found, create new user
        3. For development: grant access to dev documents if user has none
        """
        try:
            # Find existing user by email
            user = db.query(User).filter(User.email == email).first()
            
            if user:
                user_id = str(user.id)
                
                # Check if user has any documents
                doc_count = db.query(Document).filter(Document.user_id == user_id).count()
                
                if doc_count > 0:
                    logger.info("User has documents", email=email, doc_count=doc_count)
                    return user_id
                else:
                    # User exists but no documents - check if we should migrate dev documents
                    return await UserMigrationService._handle_empty_user(user, email, db)
            else:
                # User doesn't exist - create and handle migration
                return await UserMigrationService._create_user_with_migration(email, db)
                
        except Exception as e:
            logger.error("User access lookup failed", email=email, error=str(e))
            return None
    
    @staticmethod
    async def _handle_empty_user(user: User, email: str, db: Session) -> str:
        """
        Handle user with no documents - development phase logic
        """
        user_id = str(user.id)
        
        # For development: Check if this is an authorized user who should access dev documents  
        authorized_emails = [
            "augu144@gmail.com",  # Your authenticated email
            "saharcarmel@gmail.com", 
            "dev@example.com",
            # Add other authorized developer emails
        ]
        
        if email.lower() in [e.lower() for e in authorized_emails]:
            # Grant access to development documents by reassigning them
            dev_user = db.query(User).filter(User.vercel_user_id == "dev_user_1").first()
            if dev_user:
                # Reassign documents to the authenticated user
                updated_count = db.query(Document).filter(
                    Document.user_id == str(dev_user.id)
                ).update({"user_id": user_id})
                
                if updated_count > 0:
                    db.commit()
                    logger.info("Migrated dev documents to authenticated user", 
                               email=email, 
                               user_id=user_id,
                               migrated_docs=updated_count)
                    return user_id
        
        logger.info("User has no documents and migration not applicable", email=email)
        return user_id
    
    @staticmethod
    async def _create_user_with_migration(email: str, db: Session) -> str:
        """
        Create new user with potential document migration
        """
        # Create new user
        new_user = User(
            vercel_user_id=email,
            email=email,
            name=email.split("@")[0].title()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info("Created new user", email=email, user_id=str(new_user.id))
        
        # Apply migration logic for authorized users
        return await UserMigrationService._handle_empty_user(new_user, email, db)


class DocumentAccessService:
    """
    Manages document access permissions and sharing
    """
    
    @staticmethod
    async def can_access_document(
        user_id: str, 
        document_id: str, 
        db: Session
    ) -> bool:
        """
        Check if user can access specific document
        """
        try:
            document = db.query(Document).filter(
                Document.id == document_id,
                Document.user_id == user_id
            ).first()
            
            return document is not None
            
        except Exception as e:
            logger.error("Document access check failed", 
                        user_id=user_id, 
                        document_id=document_id, 
                        error=str(e))
            return False
    
    @staticmethod
    async def get_user_documents(
        user_id: str, 
        db: Session,
        limit: Optional[int] = None
    ) -> List[Document]:
        """
        Get all documents accessible by user
        """
        try:
            query = db.query(Document).filter(Document.user_id == user_id)
            
            if limit:
                query = query.limit(limit)
                
            return query.all()
            
        except Exception as e:
            logger.error("Failed to get user documents", user_id=user_id, error=str(e))
            return []