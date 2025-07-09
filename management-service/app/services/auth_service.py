"""
Authentication service implementation
"""
import logging
from typing import Optional

from app.services.interfaces import IAuthenticationService

logger = logging.getLogger(__name__)


class AuthenticationService(IAuthenticationService):
    """Authentication service implementation"""
    
    def __init__(self, api_key: Optional[str]):
        self.api_key = api_key
    
    def verify_api_key(self, api_key: str) -> bool:
        """Verify API key"""
        if not self.is_configured():
            logger.error("API key not configured")
            return False
        
        return api_key == self.api_key
    
    def is_configured(self) -> bool:
        """Check if authentication is configured"""
        return self.api_key is not None and len(self.api_key.strip()) > 0