"""
Redis Queue Service for Event Broker
"""
import json
import redis
import uuid
from typing import Dict, Any
from datetime import datetime
from app.config import config
from app.logger import setup_logger

logger = setup_logger(__name__, level=config.LOG_LEVEL)


class QueueService:
    """Redis queue service for managing rebalance events"""
    
    def __init__(self):
        self.redis = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            decode_responses=True
        )
        
    async def enqueue_event(self, account_id: str, event_data: Dict[str, Any]) -> str:
        """
        Enqueue a rebalance event if account is not already queued
        
        Returns:
            str: event_id if enqueued, None if account already queued
        """
        try:
            # Check if account already queued
            if self.redis.sismember("queued_accounts", account_id):
                logger.info(f"Account {account_id} already queued, skipping duplicate event")
                return None
            
            # Generate event ID
            event_id = str(uuid.uuid4())
            
            # Create queue event
            queue_event = {
                'event_id': event_id,
                'account_id': account_id,
                'data': event_data,
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Add to queue and tracking set atomically
            pipe = self.redis.pipeline()
            pipe.sadd("queued_accounts", account_id)
            pipe.lpush("rebalance_queue", json.dumps(queue_event))
            pipe.execute()
            
            logger.info(f"Event queued successfully", extra={
                'event_id': event_id, 
                'account_id': account_id,
                'exec_command': event_data.get('exec', 'unknown')
            })
            
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to enqueue event for account {account_id}: {e}")
            raise
    
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