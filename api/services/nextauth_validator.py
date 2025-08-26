"""
Production-grade NextAuth.js token validation for FastAPI
"""
import os
from typing import Optional, Dict, Any
import jwt
from jose import JWTError, jwt as jose_jwt
from datetime import datetime
import structlog
from fastapi import HTTPException

logger = structlog.get_logger(__name__)


class NextAuthValidator:
    """
    Production-grade NextAuth.js token validator
    """
    
    def __init__(self):
        self.secret = os.getenv("NEXTAUTH_SECRET")
        if not self.secret:
            raise ValueError("NEXTAUTH_SECRET environment variable is required")
        
        self.algorithm = "HS256"
        logger.info("NextAuth validator initialized")
    
    async def validate_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate NextAuth.js session token and return user info
        """
        try:
            # Decode and validate JWT
            payload = jose_jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                options={"verify_signature": True, "verify_exp": True}
            )
            
            # Extract user information
            user_info = {
                "user_id": payload.get("sub"),  # Subject (user ID)
                "email": payload.get("email"),
                "name": payload.get("name"),
                "image": payload.get("picture"),
                "provider": payload.get("provider", "unknown"),
                "exp": payload.get("exp"),
                "iat": payload.get("iat")
            }
            
            # Validate required fields
            if not user_info["email"]:
                raise ValueError("Email not found in token")
            
            logger.info("Token validated successfully", 
                       email=user_info["email"], 
                       provider=user_info["provider"])
            
            return user_info
            
        except JWTError as e:
            logger.warning("JWT validation failed", error=str(e), token_prefix=token[:20] if token else "None")
            return None
        except Exception as e:
            logger.error("Token validation error", error=str(e))
            return None
    
    async def validate_api_token(self, authorization_header: str) -> Optional[Dict[str, Any]]:
        """
        Extract and validate token from Authorization header
        """
        if not authorization_header:
            return None
        
        # Handle Bearer token format
        if authorization_header.startswith("Bearer "):
            token = authorization_header.split(" ")[1]
            return await self.validate_session_token(token)
        
        return None


class NextAuthCookieValidator:
    """
    Alternative validator for NextAuth.js session cookies
    """
    
    def __init__(self):
        self.secret = os.getenv("NEXTAUTH_SECRET")
        if not self.secret:
            raise ValueError("NEXTAUTH_SECRET environment variable is required")
    
    async def validate_session_cookie(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Validate NextAuth.js session cookie token
        Note: This is a simplified implementation
        In production, you might need to handle NextAuth's specific cookie encryption
        """
        try:
            # NextAuth.js sometimes uses different token formats
            # This is a basic implementation - may need adjustment based on your NextAuth config
            
            if not session_token:
                return None
            
            # For development, try to decode as JWT
            # In production, you might need NextAuth's specific decryption logic
            validator = NextAuthValidator()
            return await validator.validate_session_token(session_token)
            
        except Exception as e:
            logger.error("Cookie validation failed", error=str(e))
            return None


# Global validator instance
nextauth_validator = NextAuthValidator()


async def get_user_from_nextauth_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get user info from NextAuth token
    """
    return await nextauth_validator.validate_session_token(token)


async def get_user_from_authorization(authorization: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get user info from Authorization header
    """
    return await nextauth_validator.validate_api_token(authorization)