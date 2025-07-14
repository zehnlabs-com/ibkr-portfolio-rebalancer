import os
import yaml
from typing import Dict, Optional
from dataclasses import dataclass
import logging
import re

    # Note: Account configuration dataclasses removed - account configs now come from event payloads

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
    username: str                  # IBKR account username (from environment)
    password: str                  # IBKR account password (from environment)
    trading_mode: str              # Trading mode: 'paper' or 'live'
    connection_retry: RetryConfig  # Connection retry configuration
    order_retry: RetryConfig       # Order submission retry configuration
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
    startup_max_attempts: int    # Maximum startup retry attempts before failing
    startup_delay: int           # Seconds between startup retry attempts
    startup_initial_delay: int   # Initial delay at startup to allow services to stabilize
    retry_delay_seconds: int     # Seconds to wait before retrying failed events
    retry_check_interval: int    # Seconds between checks for ready-to-retry delayed events

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
class OrderConfig:
    """Order execution configuration (from environment variables)"""
    time_in_force: str           # Order time-in-force: 'DAY' or 'GTC'
    extended_hours_enabled: bool # Enable extended hours trading
    
class Config:
    def __init__(self, config_file: str = "config.yaml"):
        # Load configuration from YAML file (required)
        config_data = self._load_config_file(config_file)
        
        # IBKR config (YAML for app settings, env for secrets and connection details)
        ibkr_config = config_data["ibkr"]  # Required section
        self.ibkr = IBKRConfig(
            host=os.getenv("IB_HOST", ibkr_config["host"]),  # Use IB_HOST like old code
            port=int(os.getenv("IB_PORT", ibkr_config["port"])),  # Use IB_PORT like old code
            username=os.getenv("IBKR_USERNAME", ""),  # Secret from env
            password=os.getenv("IBKR_PASSWORD", ""),  # Secret from env
            trading_mode=os.getenv("TRADING_MODE", "paper"),  # Secret from env
            connection_retry=self._load_retry_config(ibkr_config["connection_retry"]),
            order_retry=self._load_retry_config(ibkr_config["order_retry"]),
            order_completion_timeout=ibkr_config.get("order_completion_timeout", 60)
        )
        
        # Redis config
        redis_config = config_data["redis"]  # Required section
        self.redis = RedisConfig(
            host=os.getenv("REDIS_HOST", redis_config["host"]),
            port=redis_config["port"],
            db=redis_config["db"],
            max_connections=redis_config["max_connections"]
        )
        
        # PostgreSQL config removed
        
        # Processing config
        processing_config = config_data["processing"]  # Required section
        self.processing = ProcessingConfig(
            queue_timeout=processing_config["queue_timeout"],
            startup_max_attempts=processing_config["startup_max_attempts"],
            startup_delay=processing_config["startup_delay"],
            startup_initial_delay=processing_config["startup_initial_delay"],
            retry_delay_seconds=processing_config.get("retry_delay_seconds", 60),
            retry_check_interval=processing_config.get("retry_check_interval", 60)
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
            level=logging_config["level"],
            format=logging_config["format"]
        )
        
        # Order config (from environment variables)
        self.order = OrderConfig(
            time_in_force=os.getenv("TIME_IN_FORCE", "DAY"),
            extended_hours_enabled=os.getenv("EXTENDED_HOURS_ENABLED", "false").lower() == "true"
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
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), config_file)
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
    
    # Note: _load_accounts method removed - account configs now come from event payloads
    
    # Note: get_account_config method removed - account configs now come from event payloads

config = Config()