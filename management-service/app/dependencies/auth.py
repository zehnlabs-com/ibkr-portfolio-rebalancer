"""
Authentication dependencies for FastAPI routes
"""
import logging
from typing import Optional
from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth_service import AuthService

# Create a single instance of the auth service
auth_service = AuthService()

# Create the security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    Dependency to get the current authenticated user from JWT token
    
    Args:
        credentials: The authorization credentials from the request
        
    Returns:
        The decoded JWT payload
        
    Raises:
        HTTPException: If the token is invalid or missing
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = auth_service.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


async def optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Optional dependency to get the current user if authenticated
    
    Args:
        credentials: The authorization credentials from the request
        
    Returns:
        The decoded JWT payload if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    return auth_service.verify_token(token)


async def websocket_auth_required(websocket: WebSocket, token: str) -> dict:
    """
    Authenticate WebSocket connection using JWT token from query parameter
    
    Args:
        websocket: The WebSocket connection
        token: JWT token from query parameter
        
    Returns:
        The decoded JWT payload if authentication succeeds
        
    Raises:
        Exception if authentication fails (WebSocket will be closed without accepting)
    """
    logger = logging.getLogger(__name__)
    
    if not token:
        logger.warning(f"WebSocket authentication failed - no token provided from {websocket.client}")
        # Don't accept the connection - just raise an exception
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    
    # Verify the JWT token using the existing auth service
    payload = auth_service.verify_token(token)
    
    if not payload:
        logger.warning(f"WebSocket authentication failed - invalid token from {websocket.client}")
        # Don't accept the connection - just raise an exception
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    
    logger.info(f"WebSocket authenticated successfully for user: {payload.get('sub')} from {websocket.client}")
    return payload