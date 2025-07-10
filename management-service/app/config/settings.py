"""
Configuration settings for management service
HTTP API for monitoring and managing the IBKR portfolio rebalancer system
"""
import os
from typing import Optional


class Settings:
    """Management service configuration
    
    All configuration comes from environment variables for deployment flexibility.
    This service provides HTTP endpoints for system monitoring and management.
    """
    
    def __init__(self):
        # Redis configuration for accessing system state
        self.redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
        
        # API security configuration
        self.management_api_key: Optional[str] = os.getenv("MANAGEMENT_API_KEY")  # Required for secured endpoints
        self.api_key_header: str = os.getenv("API_KEY_HEADER", "X-API-Key")     # HTTP header name for API key
        
        # HTTP server configuration
        self.host: str = os.getenv("HOST", "0.0.0.0")           # HTTP server bind address
        self.port: int = int(os.getenv("PORT", "8000"))         # HTTP server port
        
        # Logging configuration
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")    # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
        
    def is_api_key_configured(self) -> bool:
        """Check if API key is configured for authentication"""
        return self.management_api_key is not None and len(self.management_api_key.strip()) > 0


# Global settings instance
settings = Settings()