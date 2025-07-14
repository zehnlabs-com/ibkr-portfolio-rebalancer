"""
Configuration management for the Event Broker Service
"""
import os
import yaml
import logging
from typing import Dict
from dataclasses import dataclass


@dataclass
class RedisConfig:
    """Redis connection configuration for event queue"""
    host: str  # Redis server hostname
    port: int  # Redis server port
    db: int    # Redis database number

@dataclass
class AblyConfig:
    """Ably realtime messaging configuration"""
    api_key: str  # Ably API key for service authentication

@dataclass
class ApplicationConfig:
    """Application runtime configuration"""
    log_level: str     # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    accounts_file: str # Path to account configuration file

@dataclass
class AllocationsConfig:
    """Strategy allocation API configuration"""
    base_url: str  # Base URL for strategy allocation API

@dataclass
class RebalancerConfig:
    """Event processor API configuration"""
    api_url: str  # Event processor service URL for health checks
    timeout: int  # HTTP request timeout in seconds


class Config:
    def __init__(self, config_file: str = "config.yaml"):
        # Load configuration from YAML file (required)
        config_data = self._load_config_file(config_file)
        
        # Redis config
        redis_config = config_data["redis"]
        self.redis = RedisConfig(
            host=os.getenv("REDIS_HOST", redis_config["host"]),
            port=redis_config["port"],
            db=redis_config["db"]
        )
        
        # Ably config (environment variable required)
        api_key = os.getenv("REBALANCE_EVENT_SUBSCRIPTION_API_KEY")
        if not api_key:
            raise ValueError("REBALANCE_EVENT_SUBSCRIPTION_API_KEY environment variable is required")
        self.ably = AblyConfig(api_key=api_key)
        
        # Application config (from YAML only)
        app_config = config_data["application"]
        self.application = ApplicationConfig(
            log_level=app_config["log_level"],
            accounts_file=app_config["accounts_file"]
        )
        
        # Allocations config (from YAML only)
        allocations_config = config_data["allocations"]
        self.allocations = AllocationsConfig(
            base_url=allocations_config["base_url"]
        )
        
        # Rebalancer config (from YAML only)
        rebalancer_config = config_data["rebalancer"]
        self.rebalancer = RebalancerConfig(
            api_url=rebalancer_config["api_url"],
            timeout=rebalancer_config["timeout"]
        )
        
        # Backwards compatibility properties
        self.REALTIME_API_KEY = self.ably.api_key
        self.LOG_LEVEL = self.application.log_level
        self.ACCOUNTS_FILE = self.application.accounts_file
        self.REBALANCER_API_URL = self.rebalancer.api_url
        self.REBALANCER_API_TIMEOUT = self.rebalancer.timeout
    
    def _load_config_file(self, config_file: str) -> Dict:
        """Load configuration from YAML file - REQUIRED, no fallbacks"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), config_file)
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                raise ValueError(f"Config file {config_file} is empty")
            
            # Validate required sections exist
            required_sections = ["redis", "application", "allocations", "rebalancer"]
            for section in required_sections:
                if section not in config_data:
                    raise ValueError(f"Required configuration section '{section}' missing from {config_file}")
            
            logging.info(f"Loaded configuration from {config_file}")
            return config_data
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file {config_file} not found. This file is required.")
        except Exception as e:
            raise Exception(f"Error loading config file {config_file}: {e}")


config = Config()