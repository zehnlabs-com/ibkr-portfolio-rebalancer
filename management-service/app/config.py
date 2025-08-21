"""
Configuration management for the Management Service
"""
import os
import yaml
import logging
from typing import Dict
from dataclasses import dataclass


@dataclass
class RedisConfig:
    """Redis connection configuration for accessing system state"""
    host: str  # Redis server hostname
    port: int  # Redis server port
    db: int    # Redis database number


@dataclass
class ServerConfig:
    """HTTP server configuration"""
    host: str  # HTTP server bind address
    port: int  # HTTP server port


@dataclass
class ZehnlabsConfig:
    """Zehnlabs API configuration"""
    workers_api_url: str  # Base URL for Zehnlabs Workers API
    api_timeout: float    # HTTP request timeout in seconds


@dataclass
class AuthenticationConfig:
    """Authentication configuration"""
    clerk_frontend_api_url: str  # Clerk Frontend API URL


@dataclass
class LoggingConfig:
    """Application logging configuration"""
    level: str    # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format: str   # Log format: json or text


class Config:
    def __init__(self, config_file: str = "config.yaml"):
        # Load configuration from YAML file (required)
        config_data = self._load_config_file(config_file)
        
        # Redis config
        redis_config = config_data["redis"]
        self.redis = RedisConfig(
            host=os.getenv("REDIS_HOST", redis_config["host"]),
            port=int(os.getenv("REDIS_PORT", str(redis_config["port"]))),
            db=int(os.getenv("REDIS_DB", str(redis_config["db"])))
        )
        
        # Build Redis URL from components or use REDIS_URL if provided
        if os.getenv("REDIS_URL"):
            self.redis_url = os.getenv("REDIS_URL")
        else:
            self.redis_url = f"redis://{self.redis.host}:{self.redis.port}/{self.redis.db}"
        
        # Server config
        server_config = config_data["server"]
        self.server = ServerConfig(
            host=os.getenv("HOST", server_config["host"]),
            port=int(os.getenv("PORT", str(server_config["port"])))
        )
        
        # Zehnlabs API config
        zehnlabs_config = config_data["zehnlabs"]
        self.zehnlabs = ZehnlabsConfig(
            workers_api_url=os.getenv("ZEHNLABS_WORKERS_API_URL", zehnlabs_config["workers_api_url"]),
            api_timeout=float(os.getenv("ZEHNLABS_API_TIMEOUT", str(zehnlabs_config["api_timeout"])))
        )
        
        # Authentication config
        auth_config = config_data["authentication"]
        self.authentication = AuthenticationConfig(
            clerk_frontend_api_url=os.getenv("CLERK_FRONTEND_API_URL", auth_config["clerk_frontend_api_url"])
        )
        
        # Logging config
        logging_config = config_data["logging"]
        self.logging = LoggingConfig(
            level=os.getenv("LOG_LEVEL", logging_config["level"]),
            format=logging_config["format"]
        )
    
    def _load_config_file(self, config_file: str) -> Dict:
        """Load configuration from YAML file - REQUIRED, no fallbacks"""
        try:
            # Try current directory first
            config_path = config_file
            if not os.path.exists(config_path):
                # Try in /app for Docker environment
                config_path = os.path.join("/app", config_file)
            
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                raise ValueError(f"Config file {config_file} is empty")
            
            # Validate required sections exist
            required_sections = ["redis", "server", "zehnlabs", "authentication", "logging"]
            for section in required_sections:
                if section not in config_data:
                    raise ValueError(f"Required configuration section '{section}' missing from {config_file}")
            
            logging.info(f"Loaded configuration from {config_path}")
            return config_data
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file {config_file} not found. This file is required.")
        except Exception as e:
            raise Exception(f"Error loading config file {config_file}: {e}")


config = Config()