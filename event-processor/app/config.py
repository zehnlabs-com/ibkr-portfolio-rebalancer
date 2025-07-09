import os
import yaml
from typing import Dict, Optional
from dataclasses import dataclass
import logging
import re

    # Note: Account configuration dataclasses removed - account configs now come from event payloads

@dataclass
class RetryConfig:
    max_retries: int
    delay: int

@dataclass
class IBKRConfig:
    host: str
    port: int
    username: str
    password: str
    trading_mode: str
    connection_retry: RetryConfig
    order_retry: RetryConfig

@dataclass
class RedisConfig:
    host: str
    port: int
    db: int
    max_connections: int

# PostgreSQL configuration removed

@dataclass
class ProcessingConfig:
    max_retry_days: int
    queue_timeout: int
    startup_max_attempts: int
    startup_delay: int
    startup_initial_delay: int

@dataclass
class AllocationConfig:
    api_url: str
    timeout: int

@dataclass
class LoggingConfig:
    level: str
    format: str
    retention_days: int

@dataclass
class OrderConfig:
    order_type: str
    time_in_force: str
    extended_hours_enabled: bool
    
class Config:
    def __init__(self, config_file: str = "config/config.yaml"):
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
            order_retry=self._load_retry_config(ibkr_config["order_retry"])
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
            max_retry_days=processing_config["max_retry_days"],
            queue_timeout=processing_config["queue_timeout"],
            startup_max_attempts=processing_config["startup_max_attempts"],
            startup_delay=processing_config["startup_delay"],
            startup_initial_delay=processing_config["startup_initial_delay"]
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
            format=logging_config["format"],
            retention_days=logging_config["retention_days"]
        )
        
        # Order config (from environment variables)
        self.order = OrderConfig(
            order_type=os.getenv("ORDER_TYPE", "MKT"),
            time_in_force=os.getenv("TIME_IN_FORCE", "DAY"),
            extended_hours_enabled=os.getenv("EXTENDED_HOURS_ENABLED", "false").lower() == "true"
        )
        
        # Allocations API config (from YAML only)
        self.allocations_base_url = self.allocation.api_url
        
        # API keys (secrets from env only)
        self.zehnlabs_fintech_api_key = os.getenv("ZEHNLABS_FINTECH_API_KEY", "")
        
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