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
class AllocationsConfig:
    url: str

@dataclass
class AccountConfig:
    account_id: str
    notification: NotificationConfig
    allocations: AllocationsConfig

@dataclass
class IBKRConfig:
    host: str
    port: int
    username: str
    password: str
    trading_mode: str
    max_retries: int
    retry_delay: int

@dataclass
class APIConfig:
    host: str
    port: int
    workers: int
    
class Config:
    def __init__(self, accounts_file: str = "accounts.yaml"):
        # IBKR config (all from env vars)
        self.ibkr = IBKRConfig(
            host=os.getenv("IBKR_HOST", "127.0.0.1"),
            port=int(os.getenv("IBKR_PORT", "8888")),
            username=os.getenv("IBKR_USERNAME", ""),
            password=os.getenv("IBKR_PASSWORD", ""),
            trading_mode=os.getenv("TRADING_MODE", "paper"),
            max_retries=int(os.getenv("IBKR_MAX_RETRIES", "3")),
            retry_delay=int(os.getenv("IBKR_RETRY_DELAY", "5"))
        )
        
        # FastAPI config
        self.api = APIConfig(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            workers=int(os.getenv("API_WORKERS", "1"))
        )
        
        # Application config (all from env vars)
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # API keys
        self.allocations_api_key = os.getenv("ALLOCATIONS_API_KEY", "")
        
        # Load accounts from simple YAML file
        self.accounts: List[AccountConfig] = self._load_accounts(accounts_file)
    
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
                    
                    allocations_config = AllocationsConfig(
                        url=account_data["allocations"]["url"]
                    )
                    
                    account = AccountConfig(
                        account_id=account_data["account_id"],
                        notification=notification_config,
                        allocations=allocations_config
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