"""
Configuration management handlers for .env and accounts.yaml files
"""
import os
import yaml
from datetime import datetime
from typing import Dict, Any, List
from fastapi import HTTPException
import shutil


class ConfigHandlers:
    """Handlers for configuration file management"""
    
    def __init__(self):
        self.env_path = "/app/config/.env"
        self.accounts_path = "/app/config/accounts.yaml"
        self.backup_dir = "/app/config/backups"
        self._ensure_backup_dir()
    
    def _ensure_backup_dir(self):
        """Ensure backup directory exists"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir, exist_ok=True)
    
    def _create_backup(self, file_path: str) -> str:
        """Create a backup of the file before modification"""
        if not os.path.exists(file_path):
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        backup_path = os.path.join(self.backup_dir, f"{filename}.{timestamp}")
        
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    async def get_env_config(self) -> Dict[str, str]:
        """Get current .env configuration"""
        try:
            if not os.path.exists(self.env_path):
                return {
                    "file_exists": False,
                    "message": ".env file not found"
                }
            
            env_config = {}
            with open(self.env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_config[key] = value
            
            return {
                "file_exists": True,
                "config": env_config,
                "last_modified": datetime.fromtimestamp(os.path.getmtime(self.env_path)).isoformat()
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read .env file: {str(e)}")
    
    async def update_env_config(self, config: Dict[str, str]) -> Dict[str, Any]:
        """Update .env configuration"""
        try:
            # Create backup
            backup_path = self._create_backup(self.env_path)
            
            # Read current file to preserve structure and comments
            current_lines = []
            if os.path.exists(self.env_path):
                with open(self.env_path, 'r') as f:
                    current_lines = f.readlines()
            
            # Update or add configuration values
            updated_lines = []
            updated_keys = set()
            
            for line in current_lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and '=' in stripped:
                    key = stripped.split('=', 1)[0]
                    if key in config:
                        # Skip masked passwords - don't update if value is all asterisks
                        if config[key] and not all(c == '*' for c in config[key]):
                            updated_lines.append(f"{key}={config[key]}\n")
                        else:
                            # Keep original line for masked values
                            updated_lines.append(line)
                        updated_keys.add(key)
                    else:
                        updated_lines.append(line)
                else:
                    updated_lines.append(line)
            
            # Add new keys that weren't in the original file
            for key, value in config.items():
                if key not in updated_keys and value and not all(c == '*' for c in value):
                    updated_lines.append(f"{key}={value}\n")
            
            # Write updated file
            with open(self.env_path, 'w') as f:
                f.writelines(updated_lines)
            
            return {
                "success": True,
                "message": ".env file updated successfully",
                "backup_created": backup_path,
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update .env file: {str(e)}")
    
    async def get_accounts_config(self) -> Dict[str, Any]:
        """Get current accounts.yaml configuration"""
        try:
            if not os.path.exists(self.accounts_path):
                return {
                    "file_exists": False,
                    "message": "accounts.yaml file not found"
                }
            
            with open(self.accounts_path, 'r') as f:
                accounts_data = yaml.safe_load(f)
            
            if not accounts_data:
                accounts_data = {"accounts": []}
            
            return {
                "file_exists": True,
                "config": accounts_data,
                "total_accounts": len(accounts_data.get('accounts', [])),
                "last_modified": datetime.fromtimestamp(os.path.getmtime(self.accounts_path)).isoformat()
            }
            
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML in accounts.yaml: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read accounts.yaml: {str(e)}")
    
    async def update_accounts_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update accounts.yaml configuration"""
        try:
            # Validate configuration structure
            if 'accounts' not in config:
                raise HTTPException(status_code=400, detail="Configuration must include 'accounts' section")
            
            if not isinstance(config['accounts'], list):
                raise HTTPException(status_code=400, detail="'accounts' must be a list")
            
            # Validate each account
            for i, account in enumerate(config['accounts']):
                if not isinstance(account, dict):
                    raise HTTPException(status_code=400, detail=f"Account {i} must be an object")
                
                if 'account_id' not in account:
                    raise HTTPException(status_code=400, detail=f"Account {i} must have 'account_id'")
            
            # Create backup
            backup_path = self._create_backup(self.accounts_path)
            
            # Write updated configuration
            with open(self.accounts_path, 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
            
            return {
                "success": True,
                "message": "accounts.yaml updated successfully",
                "backup_created": backup_path,
                "total_accounts": len(config['accounts']),
                "updated_at": datetime.now().isoformat()
            }
            
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML configuration: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update accounts.yaml: {str(e)}")
    
    async def get_replacement_sets_config(self) -> Dict[str, Any]:
        """Get current replacement-sets.yaml configuration"""
        replacement_sets_path = os.path.join(self.config_dir, "replacement-sets.yaml")
        
        if not os.path.exists(replacement_sets_path):
            return {
                "file_exists": False,
                "config": {},
                "total_sets": 0,
                "set_names": []
            }
        
        try:
            with open(replacement_sets_path, 'r') as f:
                replacement_sets_data = yaml.safe_load(f)
            
            if not replacement_sets_data:
                replacement_sets_data = {}
            
            return {
                "file_exists": True,
                "config": replacement_sets_data,
                "total_sets": len(replacement_sets_data),
                "set_names": list(replacement_sets_data.keys()),
                "last_modified": datetime.fromtimestamp(os.path.getmtime(replacement_sets_path)).isoformat()
            }
            
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML in replacement-sets.yaml: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read replacement-sets.yaml: {str(e)}")
    
    async def update_replacement_sets_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update replacement-sets.yaml configuration"""
        replacement_sets_path = os.path.join(self.config_dir, "replacement-sets.yaml")
        
        # Validate the structure
        if not isinstance(config, dict):
            raise HTTPException(status_code=400, detail="Configuration must be a dictionary")
        
        # Validate replacement sets structure
        for set_name, rules in config.items():
            if not isinstance(rules, list):
                raise HTTPException(status_code=400, detail=f"Replacement set '{set_name}' must be a list of rules")
            
            for rule in rules:
                if not isinstance(rule, dict):
                    raise HTTPException(status_code=400, detail=f"Each rule in '{set_name}' must be a dictionary")
                
                required_fields = ['source', 'target', 'scale']
                for field in required_fields:
                    if field not in rule:
                        raise HTTPException(status_code=400, detail=f"Rule missing required field '{field}' in set '{set_name}'")
        
        try:
            # Create backup if file exists
            if os.path.exists(replacement_sets_path):
                backup_path = self._create_backup(replacement_sets_path)
            else:
                backup_path = ""
            
            # Write the new configuration
            with open(replacement_sets_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            return {
                "success": True,
                "backup_created": backup_path,
                "total_sets": len(config),
                "set_names": list(config.keys()),
                "updated_at": datetime.now().isoformat()
            }
            
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML configuration: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update replacement-sets.yaml: {str(e)}")
    
    async def restart_affected_services(self, config_type: str) -> Dict[str, Any]:
        """Trigger restart of services affected by configuration changes"""
        try:
            # Import here to avoid circular imports
            from app.handlers.docker_handlers import DockerHandlers
            
            docker_handlers = DockerHandlers()
            
            # Determine which services to restart based on config type
            if config_type == "env":
                # .env changes typically affect all services
                services_to_restart = ["event-broker", "event-processor"]
            elif config_type == "accounts":
                # accounts.yaml changes typically affect event services
                services_to_restart = ["event-broker", "event-processor"]
            elif config_type == "replacement-sets":
                # replacement-sets.yaml changes only affect event-processor
                services_to_restart = ["event-processor"]
            else:
                raise HTTPException(status_code=400, detail="Invalid config_type. Must be 'env', 'accounts', or 'replacement-sets'")
            
            restart_results = []
            for service in services_to_restart:
                try:
                    result = await docker_handlers.restart_container(service)
                    restart_results.append({
                        "service": service,
                        "success": True,
                        "message": result.get("message", "Restarted successfully")
                    })
                except Exception as e:
                    restart_results.append({
                        "service": service,
                        "success": False,
                        "error": str(e)
                    })
            
            success_count = sum(1 for r in restart_results if r["success"])
            
            return {
                "config_type": config_type,
                "services_restarted": success_count,
                "total_services": len(services_to_restart),
                "results": restart_results,
                "restarted_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to restart services: {str(e)}")
    
    async def get_config_backups(self) -> List[Dict[str, Any]]:
        """Get list of configuration backups"""
        try:
            if not os.path.exists(self.backup_dir):
                return []
            
            backups = []
            for filename in os.listdir(self.backup_dir):
                filepath = os.path.join(self.backup_dir, filename)
                if os.path.isfile(filepath):
                    backups.append({
                        "filename": filename,
                        "size": os.path.getsize(filepath),
                        "created": datetime.fromtimestamp(os.path.getctime(filepath)).isoformat(),
                        "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
                    })
            
            # Sort by creation time, newest first
            backups.sort(key=lambda x: x["created"], reverse=True)
            return backups
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get backup list: {str(e)}")