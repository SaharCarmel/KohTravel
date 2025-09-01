"""
Production-grade NextAuth.js token validation for FastAPI
"""
import os
import json
from typing import Optional, Dict, Any
import structlog
from fastapi import HTTPException
from hkdf import Hkdf
from jose import jwt, JWTError
from jose.jwe import decrypt

logger = structlog.get_logger(__name__)


class NextAuthValidator:
    """
    Production-grade NextAuth.js token validator with proper JWE decryption
    """
    
    def __init__(self):
        self.secret = os.getenv("NEXTAUTH_SECRET")
        if not self.secret:
            raise ValueError("NEXTAUTH_SECRET environment variable is required")
        
        logger.info("NextAuth validator initialized")
    
    def _get_encryption_key_v4(self, secret: str) -> bytes:
        """
        Generate encryption key for NextAuth.js v4
        """
        # NextAuth.js v4: empty salt, specific info string
        hkdf = Hkdf("", bytes(secret, "utf-8"))
        return hkdf.expand(b"NextAuth.js Generated Encryption Key", 32)
    
    def _get_encryption_key_v5(self, secret: str, salt: str = "__Secure-next-auth.session-token") -> bytes:
        """
        Generate encryption key for Auth.js v5 (NextAuth v5)
        """
        # Auth.js v5: cookie name as salt, different info string
        hkdf = Hkdf(bytes(salt, "utf-8"), bytes(secret, "utf-8"))
        info_string = f"Auth.js Generated Encryption Key ({salt})"
        return hkdf.expand(bytes(info_string, "utf-8"), 32)
    
    def _try_decrypt_jwe(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Try to decrypt JWE token using different key derivation methods
        """
        # List of possible salt values (cookie names)
        possible_salts = [
            "__Secure-next-auth.session-token",
            "next-auth.session-token", 
            "nextauth.session-token"
        ]
        
        # Try NextAuth v4 approach first
        try:
            encryption_key = self._get_encryption_key_v4(self.secret)
            decrypted_bytes = decrypt(token, encryption_key)
            return json.loads(decrypted_bytes.decode('utf-8'))
        except Exception as e:
            logger.debug("NextAuth v4 decryption failed", error=str(e))
        
        # Try Auth.js v5 approach with different salts
        for salt in possible_salts:
            try:
                encryption_key = self._get_encryption_key_v5(self.secret, salt)
                decrypted_bytes = decrypt(token, encryption_key)
                return json.loads(decrypted_bytes.decode('utf-8'))
            except Exception as e:
                logger.debug(f"Auth.js v5 decryption failed with salt {salt}", error=str(e))
        
        return None
    
    def _get_signing_key_jwt(self, secret: str) -> str:
        """
        Generate signing key for NextAuth.js JWT tokens
        """
        # NextAuth.js v4 uses the secret directly for JWT signing
        return secret
    
    def _validate_with_nextauth_official(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Use NextAuth.js validation endpoint for reliable token validation
        """
        try:
            import httpx
            import json
            import os
            
            # Use the frontend's NextAuth validation endpoint
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
            
            with httpx.Client(timeout=5.0) as client:
                response = client.post(
                    f"{frontend_url}/api/validate-token",
                    json={"token": token},
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        return result.get('user')
                    else:
                        logger.debug("NextAuth validation endpoint failed", error=result.get('error'))
                else:
                    logger.debug("NextAuth validation endpoint error", status_code=response.status_code)
            
        except Exception as e:
            logger.debug("NextAuth validation endpoint error", error=str(e))
        
        return None

    async def validate_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate NextAuth.js session token using official NextAuth library
        """
        try:
            # Use NextAuth.js official library for reliable token validation
            user_info = self._validate_with_nextauth_official(token)
            
            if user_info:
                return user_info
            
            # Fallback: Try manual JWE decryption as backup
            payload = self._try_decrypt_jwe(token)
            if not payload:
                logger.warning("All NextAuth validation methods failed", token_prefix=token[:20])
                return None
            
            # Extract user information from the payload
            user_info = {
                "user_id": payload.get("sub"),  # Subject (user ID)
                "email": payload.get("email"),
                "name": payload.get("name"),
                "image": payload.get("picture") or payload.get("image"),
                "provider": payload.get("provider", "unknown"),
                "exp": payload.get("exp"),
                "iat": payload.get("iat")
            }
            
            # Validate required fields
            if not user_info["email"]:
                logger.warning("Email not found in token payload", payload_keys=list(payload.keys()))
                return None
            
            logger.info("Token validated successfully", 
                       email=user_info["email"], 
                       provider=user_info["provider"],
                       token_type="JWT" if self._try_validate_jwt(token) else "JWE")
            
            return user_info
            
        except Exception as e:
            logger.error("Token validation failed", error=str(e), token_prefix=token[:20] if token else "None")
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