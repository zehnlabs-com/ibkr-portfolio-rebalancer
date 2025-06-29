# app/config.py
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    # IBKR Connection
    ibkr_host: str = "ibkr"  # Docker service name
    ibkr_port: int = 8888    # Port for extrange/ibkr image
    ibkr_client_id: int = 1  # Will be randomized in client
    ibkr_account_id: str  # IBKR account ID (e.g., DU123456) - REQUIRED
    account_type: Literal["paper", "live"] = "paper"
    
    # App Settings
    log_level: str = "INFO"
    
    # Connection settings
    connection_timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = False