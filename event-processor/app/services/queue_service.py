"""
Redis Queue Service for Event Processor
"""
import json
import redis
from typing import Dict, Any, Optional
from app.config import config
from app.logger import setup_logger

logger = setup_logger(__name__)


class QueueService:
    """Redis queue service for consuming rebalance events"""
    
    def __init__(self):
        self.redis = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            decode_responses=True
        )
        
    async def get_next_event(self) -> Optional[Dict[str, Any]]:
        """
        Get next event from queue with timeout
        
        Returns:
            Dict[str, Any]: Event data if available, None if timeout
        """
        try:
            result = self.redis.brpop(
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
            account_id = event_data['account_id']
            
            # Add to front of queue and tracking set
            pipe = self.redis.pipeline()
            pipe.lpush("rebalance_queue", json.dumps(event_data))
            pipe.sadd("queued_accounts", account_id)
            pipe.execute()
            
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
            self.redis.srem("queued_accounts", account_id)
            logger.debug(f"Removed account from queued set", extra={'account_id': account_id})
        except Exception as e:
            logger.error(f"Failed to remove account from queued set: {e}")
    
    def get_queue_length(self) -> int:
        """Get current queue length"""
        try:
            return self.redis.llen("rebalance_queue")
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0
    
    def get_queued_accounts(self) -> set:
        """Get set of currently queued account IDs"""
        try:
            return self.redis.smembers("queued_accounts")
        except Exception as e:
            logger.error(f"Failed to get queued accounts: {e}")
            return set()
    
    def is_connected(self) -> bool:
        """Check if Redis connection is active"""
        try:
            self.redis.ping()
            return True
        except Exception:
            return False