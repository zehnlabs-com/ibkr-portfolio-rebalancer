"""
Setup handlers for account configuration management
"""
import logging
import os
import yaml
import shutil
from typing import Dict, List, Any, Optional
from fastapi import HTTPException
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

class SetupHandlers:
    """Handlers for setup-related endpoints"""
    
    def __init__(self):
        self.accounts_file_path = "/app/accounts.yaml"
        self.accounts_example_path = "/app/accounts.example.yaml"
        self.env_file_path = "/app/.env"
        self.env_example_path = "/app/.env.example"
        
    async def get_main_setup_page(self) -> HTMLResponse:
        """Return the main setup page HTML"""
        try:
            template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "setup_main.html")
            with open(template_path, 'r') as f:
                html_content = f.read()
            return HTMLResponse(content=html_content)
        except Exception as e:
            logger.error(f"Failed to load main setup page: {e}")
            raise HTTPException(status_code=500, detail="Failed to load main setup page")
    
    async def get_setup_page(self) -> HTMLResponse:
        """Return the accounts setup page HTML"""
        try:
            # Use relative path that works inside the container
            template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "setup_accounts.html")
            with open(template_path, 'r') as f:
                html_content = f.read()
            return HTMLResponse(content=html_content)
        except Exception as e:
            logger.error(f"Failed to load accounts setup page: {e}")
            raise HTTPException(status_code=500, detail="Failed to load accounts setup page")
    
    async def get_env_setup_page(self) -> HTMLResponse:
        """Return the environment setup page HTML"""
        try:
            template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "setup_env.html")
            with open(template_path, 'r') as f:
                html_content = f.read()
            return HTMLResponse(content=html_content)
        except Exception as e:
            logger.error(f"Failed to load environment setup page: {e}")
            raise HTTPException(status_code=500, detail="Failed to load environment setup page")
    
    async def get_accounts_data(self) -> Dict[str, Any]:
        """Get current accounts configuration"""
        try:
            accounts_data = self._load_accounts_file()
            return {
                "accounts": accounts_data.get("accounts", []),
                "replacement_sets": accounts_data.get("replacement_sets", {})
            }
        except ValueError as e:
            # ValueError contains user-safe error messages
            logger.error(f"Configuration error loading accounts data: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error loading accounts data: {e}")
            raise HTTPException(status_code=500, detail="Unable to load account configuration")
    
    async def save_accounts(self, accounts_data: Dict[str, Any]) -> Dict[str, str]:
        """Save accounts configuration to accounts.yaml"""
        try:
            # Validate the input data
            if "accounts" not in accounts_data:
                raise ValueError("Missing 'accounts' field in request data")
            
            accounts = accounts_data["accounts"]
            if not isinstance(accounts, list):
                raise ValueError("'accounts' must be a list")
            
            # Validate each account
            for i, account in enumerate(accounts):
                self._validate_account(account, i)
            
            # Load replacement sets (from existing file or example)
            replacement_sets = self._get_replacement_sets()
            
            # Create the complete configuration
            config = {
                "accounts": accounts,
                "replacement_sets": replacement_sets
            }
            
            # Save to file
            self._save_accounts_file(config)
            
            logger.info(f"Successfully saved {len(accounts)} accounts")
            return {"message": f"Successfully saved {len(accounts)} accounts"}
            
        except ValueError as e:
            # ValueError contains user-safe error messages
            logger.error(f"Validation error: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error saving accounts: {e}")
            raise HTTPException(status_code=500, detail="Unable to save account configuration")
    
    def _load_accounts_file(self) -> Dict[str, Any]:
        """Load accounts.yaml file, return empty structure if file doesn't exist"""
        if not os.path.exists(self.accounts_file_path):
            logger.info("accounts.yaml not found, initializing empty configuration")
            return {"accounts": [], "replacement_sets": self._get_replacement_sets()}
        
        try:
            with open(self.accounts_file_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if data is None:
                logger.warning(f"accounts.yaml is empty, initializing with empty structure")
                return {"accounts": [], "replacement_sets": self._get_replacement_sets()}
            
            if not isinstance(data, dict):
                logger.error(f"accounts.yaml contains invalid data type: {type(data)}")
                raise ValueError("Configuration error: accounts.yaml must contain a YAML dictionary")
            
            # Validate structure
            if "accounts" in data and not isinstance(data["accounts"], list):
                logger.error("accounts.yaml 'accounts' field must be a list")
                raise ValueError("Configuration error: Invalid accounts.yaml structure")
            
            logger.info(f"Successfully loaded accounts.yaml with {len(data.get('accounts', []))} accounts")
            return data
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in accounts.yaml: {e}")
            raise ValueError("Configuration error: Invalid YAML format in accounts.yaml")
        except PermissionError as e:
            logger.error(f"Permission denied reading accounts.yaml: {e}")
            raise ValueError("Configuration error: Permission denied accessing accounts.yaml")
        except Exception as e:
            logger.error(f"Unexpected error reading accounts.yaml: {e}")
            raise ValueError("Configuration error: Cannot read accounts.yaml")
    
    def _get_replacement_sets(self) -> Dict[str, Any]:
        """Get replacement sets from existing accounts.yaml or accounts.example.yaml"""
        # Try to load from existing accounts.yaml first
        if os.path.exists(self.accounts_file_path):
            try:
                with open(self.accounts_file_path, 'r') as f:
                    data = yaml.safe_load(f) or {}
                    if "replacement_sets" in data:
                        logger.info("Loaded replacement_sets from existing accounts.yaml")
                        return data["replacement_sets"]
            except Exception as e:
                logger.error(f"Failed to load replacement_sets from existing accounts.yaml: {e}")
                raise ValueError(f"Configuration error: Cannot read existing accounts.yaml replacement sets")
        
        # Fallback to accounts.example.yaml
        if not os.path.exists(self.accounts_example_path):
            logger.error("accounts.example.yaml not found")
            raise ValueError("Configuration error: Required configuration template file not found")
        
        try:
            with open(self.accounts_example_path, 'r') as f:
                data = yaml.safe_load(f) or {}
                replacement_sets = data.get("replacement_sets", {})
                if not replacement_sets:
                    logger.error("No replacement_sets found in accounts.example.yaml")
                    raise ValueError("Configuration error: Invalid configuration template - missing replacement sets")
                logger.info("Loaded replacement_sets from accounts.example.yaml")
                return replacement_sets
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in accounts.example.yaml: {e}")
            raise ValueError("Configuration error: Invalid configuration template format")
        except Exception as e:
            logger.error(f"Failed to load accounts.example.yaml: {e}")
            raise ValueError("Configuration error: Cannot read configuration template")
    
    def _save_accounts_file(self, config: Dict[str, Any]) -> None:
        """Save configuration to accounts.yaml file"""
        # Validate config structure before saving
        if not isinstance(config, dict):
            logger.error(f"Invalid config type for saving: {type(config)}")
            raise ValueError("Internal error: Invalid configuration structure")
        
        if "accounts" not in config or not isinstance(config["accounts"], list):
            logger.error("Missing or invalid accounts field in configuration")
            raise ValueError("Internal error: Configuration missing accounts list")
        
        try:
            # Create backup if file exists
            if os.path.exists(self.accounts_file_path):
                backup_path = f"{self.accounts_file_path}.backup"
                try:
                    shutil.copy2(self.accounts_file_path, backup_path)
                    logger.info(f"Created backup at {backup_path}")
                except Exception as e:
                    logger.error(f"Failed to create backup: {e}")
                    raise ValueError("Configuration error: Cannot create backup of existing configuration")
            
            # Validate YAML serialization before writing
            try:
                yaml_content = yaml.dump(config, default_flow_style=False, sort_keys=False, indent=4)
            except Exception as e:
                logger.error(f"Failed to serialize configuration to YAML: {e}")
                raise ValueError("Configuration error: Cannot serialize configuration")
            
            # Save the new configuration
            try:
                with open(self.accounts_file_path, 'w') as f:
                    f.write(yaml_content)
            except PermissionError as e:
                logger.error(f"Permission denied writing to configuration file: {e}")
                raise ValueError("Configuration error: Permission denied saving configuration")
            except Exception as e:
                logger.error(f"Failed to write configuration file: {e}")
                raise ValueError("Configuration error: Cannot write configuration file")
            
            logger.info(f"Successfully saved {len(config['accounts'])} accounts to configuration file")
            
        except ValueError:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving accounts file: {e}")
            raise ValueError("Configuration error: Cannot save configuration")
    
    def _validate_account(self, account: Dict[str, Any], index: int) -> None:
        """Validate a single account configuration"""
        account_prefix = f"Account {index + 1}"
        
        # Required fields
        if not account.get("account_id"):
            raise ValueError(f"{account_prefix}: account_id is required")
        
        if not isinstance(account.get("account_id"), str):
            raise ValueError(f"{account_prefix}: account_id must be a string")
        
        # Validate account ID format (U123456 or DU123456 for paper)
        account_id = account["account_id"].strip()
        if not (account_id.startswith("U") or account_id.startswith("DU")):
            raise ValueError(f"{account_prefix}: account_id must start with 'U' (live) or 'DU' (paper)")
        
        # Set account type based on account ID
        if account_id.startswith("DU"):
            account["type"] = "paper"
        else:
            account["type"] = "live"
        
        # Validate notification channel
        notification = account.get("notification", {})
        if not notification.get("channel"):
            raise ValueError(f"{account_prefix}: notification channel is required")
        
        if not isinstance(notification["channel"], str):
            raise ValueError(f"{account_prefix}: notification channel must be a string")
        
        # Validate rebalancing configuration
        rebalancing = account.get("rebalancing", {})
        cash_reserve = rebalancing.get("cash_reserve_percent")
        
        if cash_reserve is None:
            raise ValueError(f"{account_prefix}: cash_reserve_percent is required")
        
        try:
            cash_reserve_float = float(cash_reserve)
            if cash_reserve_float < 0 or cash_reserve_float > 100:
                raise ValueError(f"{account_prefix}: cash_reserve_percent must be between 0 and 100")
            rebalancing["cash_reserve_percent"] = cash_reserve_float
        except (ValueError, TypeError):
            raise ValueError(f"{account_prefix}: cash_reserve_percent must be a valid number")
        
        # Ensure required structure exists
        account["notification"] = notification
        account["rebalancing"] = rebalancing
    
    async def get_setup_status(self) -> Dict[str, bool]:
        """Get setup completion status"""
        try:
            env_exists = os.path.exists(self.env_file_path)
            accounts_exists = os.path.exists(self.accounts_file_path)
            
            logger.info(f"Setup status check: .env exists={env_exists}, accounts.yaml exists={accounts_exists}")
            return {
                "env_exists": env_exists,
                "accounts_exists": accounts_exists
            }
        except Exception as e:
            logger.error(f"Error checking setup status: {e}")
            raise HTTPException(status_code=500, detail="Unable to check setup status")
    
    async def get_env_data(self) -> Dict[str, str]:
        """Get environment variables data"""
        try:
            env_content = self._load_env_file()
            return {"env_content": env_content}
        except Exception as e:
            logger.error(f"Error loading environment data: {e}")
            raise HTTPException(status_code=500, detail="Unable to load environment configuration")
    
    async def save_env(self, env_data: Dict[str, str]) -> Dict[str, str]:
        """Save environment variables to .env file"""
        try:
            env_content = env_data.get("env_content", "")
            
            if not env_content.strip():
                raise ValueError("Environment content cannot be empty")
            
            self._save_env_file(env_content)
            
            logger.info("Successfully saved environment configuration")
            return {"message": "Environment configuration saved successfully"}
            
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error saving environment: {e}")
            raise HTTPException(status_code=500, detail="Unable to save environment configuration")
    
    def _load_env_file(self) -> str:
        """Load .env file content, return .env.example content if .env doesn't exist"""
        # Try to load existing .env file first
        if os.path.exists(self.env_file_path):
            try:
                with open(self.env_file_path, 'r') as f:
                    content = f.read()
                logger.info("Loaded content from existing .env file")
                return content
            except PermissionError as e:
                logger.error(f"Permission denied reading .env file: {e}")
                raise ValueError("Permission denied accessing .env file")
            except Exception as e:
                logger.error(f"Error reading .env file: {e}")
                raise ValueError("Cannot read .env file")
        
        # Fallback to .env.example
        if not os.path.exists(self.env_example_path):
            logger.error(".env.example not found")
            raise ValueError("Required environment template file not found")
        
        try:
            with open(self.env_example_path, 'r') as f:
                content = f.read()
            logger.info("Loaded content from .env.example template")
            return content
        except PermissionError as e:
            logger.error(f"Permission denied reading .env.example: {e}")
            raise ValueError("Permission denied accessing environment template")
        except Exception as e:
            logger.error(f"Error reading .env.example: {e}")
            raise ValueError("Cannot read environment template")
    
    def _save_env_file(self, content: str) -> None:
        """Save content to .env file"""
        try:
            # Create backup if file exists
            if os.path.exists(self.env_file_path):
                backup_path = f"{self.env_file_path}.backup"
                try:
                    shutil.copy2(self.env_file_path, backup_path)
                    logger.info(f"Created backup at {backup_path}")
                except Exception as e:
                    logger.error(f"Failed to create backup: {e}")
                    raise ValueError("Cannot create backup of existing .env file")
            
            # Save the new content
            try:
                with open(self.env_file_path, 'w') as f:
                    f.write(content)
                logger.info("Successfully saved .env file")
            except PermissionError as e:
                logger.error(f"Permission denied writing .env file: {e}")
                raise ValueError("Permission denied saving .env file")
            except Exception as e:
                logger.error(f"Error writing .env file: {e}")
                raise ValueError("Cannot write .env file")
                
        except ValueError:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving .env file: {e}")
            raise ValueError("Cannot save environment configuration")