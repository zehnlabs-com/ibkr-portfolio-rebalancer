"""
Authentication handlers for Clerk user validation
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class UserValidationRequest(BaseModel):
    """Request model for user validation"""
    email: str

class UserValidationResponse(BaseModel):
    """Response model for user validation"""
    isAuthorized: bool
    message: str = ""

class AuthHandlers:
    """Handlers for authentication operations"""
    
    def __init__(self):
        """Initialize auth handlers"""
        self.clerk_users_file = Path("/app/clerk-users.json")
    
    async def validate_user(self, request: UserValidationRequest) -> UserValidationResponse:
        """
        Validate user against clerk-users.json file
        
        Args:
            request: User validation request
            
        Returns:
            UserValidationResponse with authorization status
        """
        try:
            logger.info(f"Validating user: {request.email}")
            
            # Check if clerk-users.json exists
            if not self.clerk_users_file.exists():
                logger.warning(f"clerk-users.json file not found at {self.clerk_users_file}")
                return UserValidationResponse(
                    isAuthorized=False,
                    message="User authorization file not found"
                )
            
            # Load authorized users (simple array of emails)
            try:
                with open(self.clerk_users_file, 'r') as f:
                    authorized_emails = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in clerk-users.json: {e}")
                return UserValidationResponse(
                    isAuthorized=False,
                    message="Invalid user authorization file format"
                )
            
            # Ensure it's a list
            if not isinstance(authorized_emails, list):
                logger.error("clerk-users.json must contain an array of email strings")
                return UserValidationResponse(
                    isAuthorized=False,
                    message="Invalid user authorization file structure"
                )
            
            # Check if user email is in the authorized list
            if request.email in authorized_emails:
                logger.info(f"User {request.email} is authorized")
                return UserValidationResponse(
                    isAuthorized=True,
                    message="User authorized"
                )
            else:
                logger.warning(f"User {request.email} not found in authorized users list")
                return UserValidationResponse(
                    isAuthorized=False,
                    message="Sorry you are not authorized to use the system"
                )
                
        except Exception as e:
            logger.error(f"Error validating user: {e}")
            return UserValidationResponse(
                isAuthorized=False,
                message=f"Error validating user: {str(e)}"
            )
