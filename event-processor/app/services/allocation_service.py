import json
import aiohttp
from typing import List, Dict
from app.config import config
from app.models.account_config import EventAccountConfig
from app.logger import setup_logger

logger = setup_logger(__name__)


class AllocationService:
    @staticmethod
    async def get_allocations(account_config: EventAccountConfig) -> List[Dict[str, float]]:
        # Construct allocations URL from base URL and channel
        allocations_url = f"{config.allocations_base_url}/{account_config.notification.channel}/allocations"
        
        api_key = config.zehnlabs_fintech_api_key
        
        headers = {}
        if api_key:            
            headers['x-telegram-user-id'] = api_key

        logger.debug(f"Retrieving allocations from {allocations_url} with API key {api_key}")
        
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
                        logger.warning(f"Total allocation is {total_allocation:.3f}, not 1.0")
                    
                    strategy_name = response_data.get("name", "Unknown")
                    strategy_long_name = response_data.get("strategy_long_name", "")
                    last_rebalance = response_data.get("last_rebalance_on", "")
                    
                    logger.info(f"Retrieved {len(allocations)} allocations for account {account_config.account_id}")
                    logger.info(f"Strategy: {strategy_name} ({strategy_long_name})")
                    if last_rebalance:
                        logger.info(f"Last rebalance: {last_rebalance}")
                    
                    return allocations
                    
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from allocation API: {e}")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error getting allocations: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting allocations: {e}")
            raise