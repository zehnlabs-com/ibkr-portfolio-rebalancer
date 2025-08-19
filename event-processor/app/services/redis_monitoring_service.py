"""
Redis Monitoring Service for Event Processor
Handles error tracking and monitoring operations in Redis
"""
import json
from typing import Dict, Any, Optional
from app.services.base_redis_service import BaseRedisService
from app.config import config
from app.logger import AppLogger

app_logger = AppLogger(__name__)


class RedisMonitoringService(BaseRedisService):
    """Service for monitoring and error tracking operations in Redis"""
    
    def __init__(self):
        """Initialize Redis Monitoring Service"""
        redis_url = f"redis://{config.redis.host}:{config.redis.port}/{config.redis.db}"
        super().__init__(redis_url=redis_url)
    
    async def store_ibkr_error(self, req_id: int, error_data: Dict[str, Any], ttl: int = 28800) -> None:
        """Store IBKR error with TTL"""
        try:
            key = f"ibkr_error:{req_id}"
            
            async def store_operation(client):
                return await client.setex(key, ttl, json.dumps(error_data))
            
            await self.execute_with_retry(store_operation)
            app_logger.log_debug(f"Stored IBKR error for request {req_id}")
        except Exception as e:
            app_logger.log_error(f"Failed to store IBKR error: {e}")
    
    async def get_ibkr_error(self, req_id: int) -> Optional[Dict[str, Any]]:
        """Get IBKR error data"""
        try:
            key = f"ibkr_error:{req_id}"
            
            async def get_operation(client):
                return await client.get(key)
            
            data = await self.execute_with_retry(get_operation)
            return json.loads(data) if data else None
        except Exception as e:
            app_logger.log_error(f"Failed to get IBKR error: {e}")
            return None
    
    async def store_order_mapping(self, req_id: int, order_id: int, ttl: int = 28800) -> None:
        """Store request ID to order ID mapping"""
        try:
            key = f"ibkr_order_mapping:{req_id}"
            
            async def store_operation(client):
                return await client.setex(key, ttl, str(order_id))
            
            await self.execute_with_retry(store_operation)
            app_logger.log_debug(f"Stored order mapping {req_id} -> {order_id}")
        except Exception as e:
            app_logger.log_error(f"Failed to store order mapping: {e}")
    
    async def get_order_mapping(self, req_id: int) -> Optional[int]:
        """Get order ID from request ID mapping"""
        try:
            key = f"ibkr_order_mapping:{req_id}"
            
            async def get_operation(client):
                return await client.get(key)
            
            data = await self.execute_with_retry(get_operation)
            return int(data) if data else None
        except Exception as e:
            app_logger.log_error(f"Failed to get order mapping: {e}")
            return None