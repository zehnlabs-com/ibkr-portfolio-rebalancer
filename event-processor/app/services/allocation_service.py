import json
import aiohttp
from typing import List, Dict
from app.config import config
from app.models.account_config import EventAccountConfig
from app.logger import AppLogger
from app.services.replacement_service import ReplacementService

app_logger = AppLogger(__name__)


class AllocationService:
    def __init__(self):
        self.replacement_service = ReplacementService()
    async def get_allocations(self, account_config: EventAccountConfig, event=None) -> List[Dict[str, float]]:        
        allocations_url = f"{config.allocations_base_url}/{account_config.strategy_name}/allocations"
        
        api_key = config.allocations_api_key
        
        headers = {}
        if api_key:            
            headers['x-api-key'] = api_key

        app_logger.log_debug(f"Retrieving allocations from {allocations_url} with API key {api_key}", event)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    allocations_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status != 200:
                        response_text = await response.text()
                        raise Exception(f"API returned status {response.status}: {response_text}")
                    
                    data = await response.json()
                    
                    if not isinstance(data, dict):
                        raise ValueError("API response must be a JSON object")
                    
                    if data.get("status") != "success":
                        raise ValueError(f"API returned error status: {data.get('status', 'unknown')}")
                    
                    response_data = data.get("data", {})
                    allocations_list = response_data.get("allocations", [])
                    
                    if not isinstance(allocations_list, list):
                        raise ValueError("API response data.allocations must be a list")
                    
                    allocations = []
                    total_allocation = 0.0
                    
                    for item in allocations_list:
                        if not isinstance(item, dict) or 'symbol' not in item or 'allocation' not in item:
                            raise ValueError("Each allocation must have 'symbol' and 'allocation' fields")
                        
                        symbol = item['symbol']
                        allocation = float(item['allocation'])
                        
                        if allocation < 0 or allocation > 1:
                            raise ValueError(f"Allocation for {symbol} must be between 0 and 1")
                        
                        allocations.append({
                            'symbol': symbol,
                            'allocation': allocation
                        })
                        
                        total_allocation += allocation
                    
                    if abs(total_allocation - 1.0) > 0.01:
                        app_logger.log_warning(f"Total allocation is {total_allocation:.3f}, not 1.0", event)
                    
                    strategy_name = response_data.get("name", "Unknown")
                    strategy_long_name = response_data.get("strategy_long_name", "")
                    last_rebalance = response_data.get("last_rebalance_on", "")
                    
                    app_logger.log_info(f"Retrieved {len(allocations)} allocations for account {account_config.account_id}", event)
                    app_logger.log_info(f"Strategy: {strategy_name} ({strategy_long_name})", event)
                    if last_rebalance:
                        app_logger.log_info(f"Last rebalance: {last_rebalance}", event)
                    
                    # Apply ETF replacements with scaling if account has replacement set configured
                    if account_config.replacement_set:
                        app_logger.log_info(f"Applying replacement set '{account_config.replacement_set}' for account {account_config.account_id}", event)
                        allocations = self.replacement_service.apply_replacements_with_scaling(
                            allocations=allocations,
                            replacement_set_name=account_config.replacement_set,
                            event=event
                        )
                        app_logger.log_info(f"Applied replacements - final allocation count: {len(allocations)}", event)
                    
                    return allocations
                    
        except json.JSONDecodeError as e:
            app_logger.log_error(f"Invalid JSON response from allocation API: {e}", event)
            raise
        except aiohttp.ClientError as e:
            app_logger.log_error(f"HTTP error getting allocations: {e}", event)
            raise
        except Exception as e:
            app_logger.log_error(f"Error getting allocations: {e}", event)
            raise