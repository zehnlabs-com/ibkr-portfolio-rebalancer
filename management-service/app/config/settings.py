"""
Configuration settings for management service
"""
import os
from typing import Optional


class Settings:
    """Application settings"""
    
    def __init__(self):
        self.redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.management_api_key: Optional[str] = os.getenv("MANAGEMENT_API_KEY")
        self.api_key_header: str = "X-API-Key"
        self.host: str = "0.0.0.0"
        self.port: int = 8000
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        
    def is_api_key_configured(self) -> bool:
        """Check if API key is configured"""
        return self.management_api_key is not None and len(self.management_api_key.strip()) > 0


# Global settings instance
settings = Settings()