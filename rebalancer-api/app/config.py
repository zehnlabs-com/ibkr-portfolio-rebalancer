import os
import yaml
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging
import re

@dataclass
class NotificationConfig:
    channel: str

@dataclass
class RebalancingConfig:
    equity_reserve_percentage: float

@dataclass
class AccountConfig:
    account_id: str
    notification: NotificationConfig
    rebalancing: RebalancingConfig

@dataclass
class RetryConfig:
    max_retries: int
    base_delay: int
    max_delay: int
    backoff_multiplier: float
    jitter: bool

@dataclass
class IBKRConfig:
    host: str
    port: int
    username: str
    password: str
    trading_mode: str
    connection_retry: RetryConfig
    market_data_retry: RetryConfig
    order_retry: RetryConfig

@dataclass
class APIConfig:
    host: str
    port: int
    workers: int
    
class Config:
    def __init__(self, accounts_file: str = "accounts.yaml", config_file: str = "config.yaml"):
        # Load configuration from YAML file (required)
        config_data = self._load_config_file(config_file)
        
        # IBKR config (YAML for app settings, env for secrets only)
        ibkr_config = config_data["ibkr"]  # Required section
        self.ibkr = IBKRConfig(
            host=ibkr_config["host"],
            port=ibkr_config["port"],
            username=os.getenv("IBKR_USERNAME", ""),  # Secret from env
            password=os.getenv("IBKR_PASSWORD", ""),  # Secret from env
            trading_mode=os.getenv("TRADING_MODE", "paper"),  # Secret from env
            connection_retry=self._load_retry_config(ibkr_config["connection_retry"]),
            market_data_retry=self._load_retry_config(ibkr_config["market_data_retry"]),
            order_retry=self._load_retry_config(ibkr_config["order_retry"])
        )
        
        # FastAPI config (from YAML only)
        api_config = config_data["api"]  # Required section
        self.api = APIConfig(
            host=api_config["host"],
            port=api_config["port"],
            workers=api_config["workers"]
        )
        
        # Application config (from YAML only)
        app_config = config_data["application"]  # Required section
        self.log_level = app_config["log_level"]
        self.connection_check_interval = app_config["connection_check_interval"]
        self.startup_max_attempts = app_config["startup_max_attempts"]
        self.startup_delay = app_config["startup_delay"]
        
        # Allocations API config (from YAML only)
        allocations_config = config_data["allocations"]  # Required section
        self.allocations_base_url = allocations_config["base_url"]
        
        # API keys (secrets from env only)
        self.allocations_api_key = os.getenv("ALLOCATIONS_API_KEY", "")
        
        # Load accounts from accounts.yaml file
        self.accounts: List[AccountConfig] = self._load_accounts(accounts_file)
    
    def _load_config_file(self, config_file: str) -> Dict:
        """Load configuration from YAML file - REQUIRED, no fallbacks"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), config_file)
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                raise ValueError(f"Config file {config_file} is empty")
            
            # Validate required sections exist
            required_sections = ["ibkr", "api", "application", "allocations"]
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
            base_delay=retry_config["base_delay"],
            max_delay=retry_config["max_delay"],
            backoff_multiplier=retry_config["backoff_multiplier"],
            jitter=retry_config["jitter"]
        )
    
    def _load_accounts(self, accounts_file: str) -> List[AccountConfig]:
        accounts = []
        
        try:
            accounts_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), accounts_file)
            with open(accounts_path, 'r') as f:
                accounts_data = yaml.safe_load(f)
            
            if not accounts_data:
                logging.warning(f"No accounts found in {accounts_file}")
                return []
            
            for account_data in accounts_data:
                try:
                    notification_config = NotificationConfig(
                        channel=account_data["notification"]["channel"]
                    )
                    
                    # Load rebalancing config with validation
                    rebalancing_data = account_data.get("rebalancing", {})
                    reserve_percentage = rebalancing_data.get("equity_reserve_percentage", 1.0)
                    # Validate reserve percentage: 0-10%, use 1% default for invalid values
                    if not (0.0 <= reserve_percentage <= 10.0):
                        logging.warning(f"Invalid equity_reserve_percentage: {reserve_percentage}% for account {account_data['account_id']}. Using default 1%.")
                        reserve_percentage = 1.0
                    
                    rebalancing_config = RebalancingConfig(
                        equity_reserve_percentage=reserve_percentage
                    )
                    
                    account = AccountConfig(
                        account_id=account_data["account_id"],
                        notification=notification_config,
                        rebalancing=rebalancing_config
                    )
                    
                    accounts.append(account)
                    
                except KeyError as e:
                    logging.error(f"Missing required field in account config: {e}")
                    continue
                    
        except FileNotFoundError:
            logging.warning(f"Accounts file {accounts_file} not found")
        except Exception as e:
            logging.error(f"Error loading accounts file: {e}")
        
        return accounts
    
    def get_account_config(self, account_id: str) -> Optional[AccountConfig]:
        for account in self.accounts:
            if account.account_id == account_id:
                return account
        return None

config = Config()