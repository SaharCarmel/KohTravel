"""
Production-grade authentication service with proper NextAuth integration
"""
from fastapi import Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from typing import Optional
import structlog

from database import get_db
from models.user import User
from .nextauth_validator import get_user_from_authorization

logger = structlog.get_logger(__name__)


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Get authenticated user from NextAuth.js session
    """
    
    logger.info("Authentication attempt", 
                has_auth_header=bool(authorization),
                auth_header_prefix=authorization[:20] if authorization else None,
                cookies=list(request.cookies.keys()))
    
    # Method 1: Try Authorization header (for API calls)
    if authorization:
        logger.info("Trying Authorization header authentication")
        user_info = await get_user_from_authorization(authorization)
        if user_info:
            logger.info("Authorization header authentication successful", email=user_info.get("email"))
            return await get_or_create_user_from_nextauth(user_info, db)
        else:
            logger.warning("Authorization header authentication failed")
    
    # Method 2: Try to get session from cookies (for browser requests)
    session_token = None
    
    # NextAuth.js stores session in cookies with different names based on configuration
    cookie_names = [
        "next-auth.session-token",
        "__Secure-next-auth.session-token",
        "nextauth.session-token"
    ]
    
    found_cookie_name = None
    for cookie_name in cookie_names:
        session_token = request.cookies.get(cookie_name)
        if session_token:
            found_cookie_name = cookie_name
            break
    
    if session_token:
        logger.info("Trying cookie authentication", 
                   cookie_name=found_cookie_name,
                   token_prefix=session_token[:20])
        from .nextauth_validator import get_user_from_nextauth_token
        user_info = await get_user_from_nextauth_token(session_token)
        if user_info:
            logger.info("Cookie authentication successful", email=user_info.get("email"))
            return await get_or_create_user_from_nextauth(user_info, db)
        else:
            logger.warning("Cookie authentication failed")
    
    logger.error("All authentication methods failed")
    raise HTTPException(
        status_code=401, 
        detail="Authentication required. Please sign in with Google or GitHub."
    )


async def get_or_create_user_from_nextauth(
    user_info: dict, 
    db: Session
) -> User:
    """
    Create or get user from NextAuth user information
    """
    try:
        email = user_info.get("email")
        name = user_info.get("name", "")
        provider_id = user_info.get("user_id") or email
        
        if not email:
            raise ValueError("Email is required from NextAuth token")
        
        # Try to find existing user by email or provider ID
        user = db.query(User).filter(
            (User.email == email) | (User.vercel_user_id == provider_id)
        ).first()
        
        if user:
            # Update user info if it has changed
            if user.email != email or user.name != name:
                user.email = email
                user.name = name
                db.commit()
                db.refresh(user)
                logger.info("Updated user info", email=email, user_id=str(user.id))
            
            return user
        
        # Create new user
        new_user = User(
            vercel_user_id=provider_id,
            email=email,
            name=name
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info("Created new authenticated user", 
                   email=email, 
                   user_id=str(new_user.id),
                   provider=user_info.get("provider"))
        
        return new_user
        
    except Exception as e:
        logger.error("Failed to create/get user from NextAuth", error=str(e), user_info=user_info)
        raise HTTPException(
            status_code=500, 
            detail="Failed to process user authentication"
        )


async def get_development_user(db: Session) -> User:
    """
    Get development user - REMOVE IN PRODUCTION
    """
    dev_user = db.query(User).filter(User.vercel_user_id == "dev_user_1").first()
    
    if not dev_user:
        dev_user = User(
            vercel_user_id="dev_user_1",
            email="dev@example.com",
            name="Development User"
        )
        db.add(dev_user)
        db.commit()
        db.refresh(dev_user)
    
    return dev_user



async def get_user_for_agent(email: str, db: Session) -> Optional[str]:
    """
    Get user UUID for agent tools - proper user lookup
    """
    try:
        # Find user by email
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            return str(user.id)
        
        # For development: if user not found, check if it should be mapped to dev user
        # This is temporary until all users are properly migrated
        if "@" in email:  # Basic email validation
            logger.info("User not found for agent, creating new user", email=email)
            
            # Create user for agent access
            new_user = User(
                vercel_user_id=email,
                email=email,
                name=email.split("@")[0].title()  # Use email prefix as name
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            return str(new_user.id)
        
        return None
        
    except Exception as e:
        logger.error("Failed to get user for agent", email=email, error=str(e))
        return None


class AuthenticationError(Exception):
    """Custom authentication error"""
    pass


class AuthorizationError(Exception):
    """Custom authorization error"""
    pass