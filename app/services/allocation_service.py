import aiohttp
import json
from typing import List, Dict
from app.config import AccountConfig
from app.logger import setup_logger

logger = setup_logger(__name__)

class AllocationService:
    @staticmethod
    async def get_allocations(account_config: AccountConfig) -> List[Dict[str, float]]:
        if not account_config.allocations.url:
            raise ValueError(f"No allocations URL configured for account {account_config.account_id}")
        
        # Use global API key
        from app.config import config
        api_key = config.allocations_api_key
        
        headers = {}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
            headers['x-telegram-user-id'] = api_key
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    account_config.allocations.url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status != 200:
                        raise Exception(f"API returned status {response.status}: {await response.text()}")
                    
                    data = await response.json()
                    
                    # Validate the response format
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
                    
                    # Validate total allocation
                    if abs(total_allocation - 1.0) > 0.01:
                        logger.warning(f"Total allocation is {total_allocation:.3f}, not 1.0")
                    
                    # Log strategy information if available
                    strategy_name = response_data.get("name", "Unknown")
                    strategy_long_name = response_data.get("strategy_long_name", "")
                    last_rebalance = response_data.get("last_rebalance_on", "")
                    
                    logger.info(f"Retrieved {len(allocations)} allocations for account {account_config.account_id}")
                    logger.info(f"Strategy: {strategy_name} ({strategy_long_name})")
                    if last_rebalance:
                        logger.info(f"Last rebalance: {last_rebalance}")
                    
                    return allocations
                    
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error getting allocations: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from allocation API: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting allocations: {e}")
            raise