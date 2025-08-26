from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
import jwt
import os

from database import get_db
from models.user import User

# This would typically come from NextAuth.js JWT
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from JWT token
    In production, this should validate NextAuth.js tokens
    """
    
    # For development, we'll create a mock user
    # In production, you would validate the JWT token from NextAuth.js
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    try:
        # Extract token from "Bearer <token>"
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        token = authorization.split(" ")[1]
        
        # For now, mock user validation
        # In production, decode and validate NextAuth.js JWT
        
        # Create or get mock user for development
        mock_user = db.query(User).filter(User.vercel_user_id == "dev_user_1").first()
        
        if not mock_user:
            mock_user = User(
                vercel_user_id="dev_user_1",
                email="dev@example.com",
                name="Development User"
            )
            db.add(mock_user)
            db.flush()  # Use flush instead of commit to avoid transaction conflicts
            db.refresh(mock_user)
        
        return mock_user
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

def verify_nextauth_token(token: str) -> dict:
    """
    Verify NextAuth.js JWT token
    This should be implemented when NextAuth.js is properly configured
    """
    # This is a placeholder - implement actual NextAuth.js token verification
    # You would need the NextAuth.js secret and proper JWT validation
    
    try:
        # Decode JWT with NextAuth secret
        secret = os.getenv("NEXTAUTH_SECRET")
        if not secret:
            raise Exception("NEXTAUTH_SECRET not configured")
        
        # For now, return mock payload
        return {
            "sub": "dev_user_1",
            "email": "dev@example.com",
            "name": "Development User"
        }
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")

def create_or_get_user(user_info: dict, db: Session) -> User:
    """Create or get user from auth provider info"""
    
    vercel_user_id = user_info.get("sub")
    if not vercel_user_id:
        raise HTTPException(status_code=400, detail="Invalid user info")
    
    # Try to find existing user
    user = db.query(User).filter(User.vercel_user_id == vercel_user_id).first()
    
    if not user:
        # Create new user
        user = User(
            vercel_user_id=vercel_user_id,
            email=user_info.get("email"),
            name=user_info.get("name")
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return user