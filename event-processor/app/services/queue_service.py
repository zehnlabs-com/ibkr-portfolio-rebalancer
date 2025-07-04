"""
Redis Queue Service for Event Processor
"""
import json
import redis.asyncio as redis
from typing import Dict, Any, Optional
from app.config import config
from app.logger import setup_logger

logger = setup_logger(__name__)


class QueueService:
    """Redis queue service for consuming rebalance events"""
    
    def __init__(self):
        self.redis = None
        self._redis_url = f"redis://{config.redis.host}:{config.redis.port}/{config.redis.db}"
    
    async def _get_redis(self):
        """Get or create Redis connection"""
        if self.redis is None:
            self.redis = await redis.from_url(self._redis_url, decode_responses=True)
        return self.redis
        
    async def get_next_event(self) -> Optional[Dict[str, Any]]:
        """
        Get next event from queue with timeout
        
        Returns:
            Dict[str, Any]: Event data if available, None if timeout
        """
        try:
            redis = await self._get_redis()
            result = await redis.brpop(
                "rebalance_queue", 
                timeout=config.processing.queue_timeout
            )
            
            if result:
                queue_name, event_json = result
                event_data = json.loads(event_json)
                logger.debug(f"Retrieved event from queue", extra={
                    'event_id': event_data.get('event_id'),
                    'account_id': event_data.get('account_id')
                })
                return event_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get event from queue: {e}")
            return None
    
    async def requeue_event(self, event_data: Dict[str, Any]):
        """
        Put event back in queue for retry (at front of queue)
        """
        try:
            redis = await self._get_redis()
            account_id = event_data['account_id']
            
            # Add to front of queue and tracking set
            pipe = redis.pipeline()
            pipe.lpush("rebalance_queue", json.dumps(event_data))
            pipe.sadd("queued_accounts", account_id)
            await pipe.execute()
            
            logger.info(f"Event requeued for retry", extra={
                'event_id': event_data.get('event_id'),
                'account_id': account_id
            })
            
        except Exception as e:
            logger.error(f"Failed to requeue event: {e}")
            raise
    
    async def remove_from_queued(self, account_id: str):
        """Remove account from queued set"""
        try:
            redis = await self._get_redis()
            await redis.srem("queued_accounts", account_id)
            logger.debug(f"Removed account from queued set", extra={'account_id': account_id})
        except Exception as e:
            logger.error(f"Failed to remove account from queued set: {e}")
    
    async def get_queue_length(self) -> int:
        """Get current queue length"""
        try:
            redis = await self._get_redis()
            return await redis.llen("rebalance_queue")
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0
    
    async def get_queued_accounts(self) -> set:
        """Get set of currently queued account IDs"""
        try:
            redis = await self._get_redis()
            return await redis.smembers("queued_accounts")
        except Exception as e:
            logger.error(f"Failed to get queued accounts: {e}")
            return set()
    
    async def is_connected(self) -> bool:
        """Check if Redis connection is active"""
        try:
            redis = await self._get_redis()
            await redis.ping()
            return True
        except Exception:
            return False