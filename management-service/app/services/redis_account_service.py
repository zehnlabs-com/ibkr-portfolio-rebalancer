"""
Redis Account Service for Management Service
Handles all account data operations in Redis
"""
import json
import logging
from typing import Dict, Any, List, Optional, AsyncIterator

from app.services.base_redis_service import BaseRedisService
from app.models.account_data import AccountData, DashboardSummary

logger = logging.getLogger(__name__)


class RedisAccountService(BaseRedisService):
    """Service for account data operations in Redis"""
    
    def __init__(self, redis_url: str):
        """Initialize Redis Account Service"""
        super().__init__(redis_url)
    
    async def get_all_accounts_data(self) -> List[AccountData]:
        """Get all account data from Redis"""
        try:
            async def get_accounts(client):
                # Get all keys matching account pattern
                account_keys = await client.keys("account:*")
                account_data_list = []
                
                for key in account_keys:
                    try:
                        data = await client.get(key)
                        if data:
                            account_dict = json.loads(data)
                            try:
                                account_obj = AccountData.from_dict(account_dict)
                                account_data_list.append(account_obj)
                            except Exception:
                                # Fallback: create basic AccountData from available fields
                                account_obj = AccountData(
                                    account_id=account_dict.get('account_id', ''),
                                    net_liquidation=account_dict.get('net_liquidation', 0.0),
                                    total_cash=account_dict.get('total_cash', 0.0),
                                    unrealized_pnl=account_dict.get('unrealized_pnl', 0.0),
                                    realized_pnl=account_dict.get('realized_pnl', 0.0),
                                    todays_pnl=account_dict.get('todays_pnl', 0.0),
                                    gross_position_value=account_dict.get('gross_position_value', 0.0),
                                    positions=account_dict.get('positions', [])
                                )
                                account_data_list.append(account_obj)
                    except (json.JSONDecodeError, Exception) as e:
                        logger.warning(f"Failed to parse account data for {key}: {e}")
                        continue
                
                return account_data_list
            
            return await self.execute_with_retry(get_accounts)
        except Exception as e:
            logger.error(f"Failed to get all accounts data: {e}")
            return []
    
    async def get_account_data(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get specific account data"""
        try:
            async def get_account(client):
                data = await client.get(f"account:{account_id}")
                if data:
                    account_dict = json.loads(data)
                    try:
                        account_obj = AccountData.from_dict(account_dict)
                        return account_obj.to_dict()
                    except Exception:
                        # Return raw data if AccountData parsing fails
                        return account_dict
                return None
            
            return await self.execute_with_retry(get_account)
        except Exception as e:
            logger.error(f"Failed to get account data for {account_id}: {e}")
            return None
    
    async def subscribe_to_updates(self) -> AsyncIterator[Dict[str, Any]]:
        """Subscribe to dashboard updates via Redis pub/sub"""
        try:
            client = await self._get_client()
            pubsub = client.pubsub()
            await pubsub.subscribe("dashboard_updates")
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        yield data
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in dashboard update: {message['data']}")
                        continue
        except Exception as e:
            logger.error(f"Failed to subscribe to updates: {e}")
    
    async def update_account_data(self, account_id: str, account_data: AccountData) -> None:
        """Update account data in Redis"""
        try:
            async def update_account(client):
                return await client.set(f"account:{account_id}", json.dumps(account_data.to_dict()))
            
            await self.execute_with_retry(update_account)
            logger.debug(f"Updated account data for {account_id}")
        except Exception as e:
            logger.error(f"Failed to update account data for {account_id}: {e}")
            raise
    
    async def update_dashboard_summary(self, summary: DashboardSummary) -> None:
        """Update dashboard summary data"""
        try:
            async def update_summary(client):
                return await client.set("dashboard:summary", json.dumps(summary.to_dict()))
            
            await self.execute_with_retry(update_summary)
            logger.debug("Updated dashboard summary")
        except Exception as e:
            logger.error(f"Failed to update dashboard summary: {e}")
            raise
    
    async def publish_dashboard_update(self, message: Dict[str, Any]) -> None:
        """Publish dashboard update message"""
        try:
            async def publish_update(client):
                return await client.publish("dashboard_updates", json.dumps(message))
            
            await self.execute_with_retry(publish_update)
            logger.debug(f"Published dashboard update: {message.get('type', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to publish dashboard update: {e}")
            raise