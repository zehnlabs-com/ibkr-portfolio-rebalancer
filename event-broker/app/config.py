"""
Configuration management for the Event Broker Service
"""
import os
from typing import Optional


class Config:
    # Service Configuration
    REBALANCER_API_URL: str = os.getenv('REBALANCER_API_URL', 'http://rebalancer-api:8000')
    REBALANCER_API_TIMEOUT: int = int(os.getenv('REBALANCER_API_TIMEOUT', '60'))
    
    # Ably Configuration
    REALTIME_API_KEY: str = os.getenv('REALTIME_API_KEY', '')
    
    # Application Settings
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # Account Configuration
    ACCOUNTS_FILE: str = os.getenv('ACCOUNTS_FILE', 'accounts.yaml')


config = Config()