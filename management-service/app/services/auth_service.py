"""
Authentication service for JWT token validation using Clerk's JWKS
"""
import logging
from typing import Optional
import jwt
from jwt import PyJWKClient
from app.config import config

logger = logging.getLogger(__name__)


class AuthService:
    """Service for JWT token validation using Clerk's JWKS"""
    
    def __init__(self):
        """Initialize the auth service with Clerk's JWKS endpoint"""
        clerk_frontend_api_url = config.authentication.clerk_frontend_api_url
        self.jwks_url = f"{clerk_frontend_api_url}/.well-known/jwks.json"
        self.jwks_client = PyJWKClient(self.jwks_url, cache_jwk_set=True, cache_keys=True, lifespan=3600)
        self.issuer = clerk_frontend_api_url
        logger.info(f"Initialized AuthService with JWKS URL: {self.jwks_url}")
    
    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verify a JWT token using Clerk's JWKS
        
        Args:
            token: The JWT token to verify
            
        Returns:
            Decoded JWT payload if valid, None otherwise
        """
        try:
            # Get signing key from token
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decode and verify token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self.issuer
            )
            
            logger.debug(f"Successfully verified token for sub: {payload.get('sub')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            return None