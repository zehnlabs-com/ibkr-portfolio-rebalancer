"""
Authentication middleware for FastAPI
"""
from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.interfaces import IAuthenticationService

security = HTTPBearer()


class AuthenticationMiddleware:
    """Authentication middleware"""
    
    def __init__(self, auth_service: IAuthenticationService):
        self.auth_service = auth_service
    
    def verify_api_key(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
        """Verify API key for protected endpoints"""
        if not self.auth_service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Management API key not configured"
            )
        
        if not self.auth_service.verify_api_key(credentials.credentials):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        return credentials.credentials
    
    def optional_verify_api_key(self, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[str]:
        """Optional API key verification"""
        if credentials:
            return self.verify_api_key(credentials)
        return None