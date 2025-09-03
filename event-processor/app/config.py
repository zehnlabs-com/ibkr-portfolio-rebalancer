import os
import yaml
from typing import Dict, Optional
from dataclasses import dataclass
import logging
@dataclass
class RetryConfig:
    """Retry behavior configuration for network operations"""
    max_retries: int  # Number of retry attempts before giving up
    delay: int        # Seconds to wait between retry attempts

@dataclass
class IBKRConfig:
    """Interactive Brokers API connection configuration"""
    host: str                      # IBKR Gateway/TWS hostname
    port: int                      # IBKR API port number
    trading_mode: str              # Trading mode: 'paper' or 'live'
    connection_retry: RetryConfig  # Connection retry configuration    
    order_completion_timeout: int  # Seconds to wait for sell orders to complete

@dataclass
class RedisConfig:
    """Redis connection configuration for event queue"""
    host: str            # Redis server hostname
    port: int            # Redis server port
    db: int              # Redis database number
    max_connections: int # Maximum connection pool size

# PostgreSQL configuration removed

@dataclass
class ProcessingConfig:
    """Event processing behavior configuration"""
    queue_timeout: int           # Seconds to wait for new events from Redis queue
    max_concurrent_events: int   # Maximum number of events to process concurrently

@dataclass
class AllocationConfig:
    """Strategy allocation API configuration"""
    api_url: str  # Base URL for strategy allocation API
    timeout: int  # HTTP request timeout in seconds

@dataclass
class LoggingConfig:
    """Application logging configuration"""
    level: str    # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format: str   # Log format: json or text

@dataclass
class UserNotificationConfig:
    """User notification service configuration"""
    enabled: bool              # Enable/disable notifications
    server_url: str           # ntfy.sh server URL
    auth_token: Optional[str] # Optional auth token
    buffer_seconds: int       # Notification buffer time in seconds
    channel_prefix: str       # Channel name prefix for notifications
    
class Config:
    def __init__(self, config_file: str = "config.yaml"):
        # Load configuration from YAML file (required)
        config_data = self._load_config_file(config_file)
        
        # IBKR config (YAML for app settings, env for secrets and connection details)
        ibkr_config = config_data["ibkr"]  # Required section
        trading_mode = os.getenv("TRADING_MODE", "paper")  # Get trading mode first
        self.ibkr = IBKRConfig(
            host=os.getenv("IB_HOST", ibkr_config["host"]),  # Use IB_HOST like old code
            port=4003 if trading_mode == "live" else 4004,  # 4003 for live, 4004 for paper
            trading_mode=trading_mode,  # From environment
            connection_retry=self._load_retry_config(ibkr_config["connection_retry"]),            
            order_completion_timeout=ibkr_config.get("order_completion_timeout", 300)
        )
        
        # Redis config
        redis_config = config_data["redis"]  # Required section
        self.redis = RedisConfig(
            host=redis_config["host"],
            port=redis_config["port"],
            db=redis_config["db"],
            max_connections=redis_config["max_connections"]
        )
        
        # PostgreSQL config removed
        
        # Processing config
        processing_config = config_data["processing"]  # Required section
        self.processing = ProcessingConfig(
            queue_timeout=processing_config["queue_timeout"],
            max_concurrent_events=processing_config.get("max_concurrent_events", 3)
        )
        
        # Allocation config
        allocation_config = config_data["allocation"]  # Required section
        self.allocation = AllocationConfig(
            api_url=allocation_config["api_url"],
            timeout=allocation_config["timeout"]
        )
        
        # Logging config 
        logging_config = config_data["logging"]  # Required section
        self.logging = LoggingConfig(
            level=os.getenv("LOG_LEVEL", logging_config["level"]),
            format=logging_config["format"]
        )
        
        # User notification config (from environment variables)
        self.user_notification = UserNotificationConfig(
            enabled=os.getenv("USER_NOTIFICATIONS_ENABLED", "true").lower() == "true",
            server_url=os.getenv("USER_NOTIFICATIONS_SERVER_URL", "https://ntfy.sh"),
            auth_token=os.getenv("USER_NOTIFICATIONS_AUTH_TOKEN"),
            buffer_seconds=int(os.getenv("USER_NOTIFICATIONS_BUFFER_SECONDS", "60")),
            channel_prefix=os.getenv("USER_NOTIFICATIONS_CHANNEL_PREFIX", "ZLF-2025")
        )
        
        # Allocations API config (from YAML only)
        self.allocations_base_url = self.allocation.api_url
        
        # API keys (secrets from env only)
        self.allocations_api_key = os.getenv("ALLOCATIONS_API_KEY", "")
        
        # Note: Account configurations are now loaded from event payloads
        # No longer loading accounts from accounts.yaml file
    
    def _load_config_file(self, config_file: str) -> Dict:
        """Load configuration from YAML file - REQUIRED, no fallbacks"""
        try:
            config_path = os.path.join("/app/config", config_file)
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                raise ValueError(f"Config file {config_file} is empty")
            
            # Validate required sections exist
            required_sections = ["ibkr", "redis", "processing", "allocation", "logging"]
            for section in required_sections:
                if section not in config_data:
                    raise ValueError(f"Required configuration section '{section}' missing from {config_file}")
            
            logging.info(f"Loaded configuration from {config_file}")
            return config_data
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file {config_file} not found. This file is required.")
        except Exception as e:
            raise Exception(f"Error loading config file {config_file}: {e}")
    
    def _load_retry_config(self, retry_config: Dict) -> RetryConfig:
        """Load retry configuration from YAML - no environment overrides"""
        return RetryConfig(
            max_retries=retry_config["max_retries"],
            delay=retry_config["delay"]
        )
    
config = Config()