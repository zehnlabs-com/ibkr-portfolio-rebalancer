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
        
        
        # HTTP server configuration
        self.host: str = os.getenv("HOST", "0.0.0.0")           # HTTP server bind address
        self.port: int = int(os.getenv("PORT", "8000"))         # HTTP server port
        
        # Logging configuration
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")    # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
        


# Global settings instance
settings = Settings()