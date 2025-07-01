"""
Configuration management for the Event Broker Service
"""
import os
import yaml
import logging
from typing import Dict
from dataclasses import dataclass


@dataclass
class RebalancerAPIConfig:
    url: str
    timeout: int


@dataclass
class AblyConfig:
    api_key: str


@dataclass
class ApplicationConfig:
    log_level: str
    accounts_file: str


class Config:
    def __init__(self, config_file: str = "config.yaml"):
        # Load configuration from YAML file (required)
        config_data = self._load_config_file(config_file)
        
        # Rebalancer API config (from YAML only)
        rebalancer_config = config_data["rebalancer_api"]
        self.rebalancer_api = RebalancerAPIConfig(
            url=rebalancer_config["url"],
            timeout=rebalancer_config["timeout"]
        )
        
        # Ably config (from YAML only - not user configurable)
        ably_config = config_data["ably"]
        self.ably = AblyConfig(
            api_key=ably_config["api_key"]
        )
        
        # Application config (from YAML only)
        app_config = config_data["application"]
        self.application = ApplicationConfig(
            log_level=app_config["log_level"],
            accounts_file=app_config["accounts_file"]
        )
        
        # Backwards compatibility properties
        self.REBALANCER_API_URL = self.rebalancer_api.url
        self.REBALANCER_API_TIMEOUT = self.rebalancer_api.timeout
        self.REALTIME_API_KEY = self.ably.api_key
        self.LOG_LEVEL = self.application.log_level
        self.ACCOUNTS_FILE = self.application.accounts_file
    
    def _load_config_file(self, config_file: str) -> Dict:
        """Load configuration from YAML file - REQUIRED, no fallbacks"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), config_file)
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                raise ValueError(f"Config file {config_file} is empty")
            
            # Validate required sections exist
            required_sections = ["rebalancer_api", "ably", "application"]
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