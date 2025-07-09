"""
Redis Queue Service for Event Broker
"""
import json
import redis
import uuid
from typing import Dict, Any
from datetime import datetime, timezone
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
        Enqueue a rebalance event if account+command combination is not already queued
        
        Returns:
            str: event_id if enqueued, None if account+command already queued
        """
        try:
            # Extract command from event data - required field
            exec_command = event_data.get('exec')
            if not exec_command:
                logger.error(f"Event missing required 'exec' field for account {account_id}, skipping event", extra={
                    'account_id': account_id,
                    'event_data': event_data
                })
                return None
            
            # Create deduplication key: account_id:exec_command
            deduplication_key = f"{account_id}:{exec_command}"
            
            # Check if account+command already queued
            if self.redis.sismember("active_events", deduplication_key):
                logger.info(f"Account {account_id} with command {exec_command} already queued, skipping duplicate event")
                return None
            
            # Generate event ID
            event_id = str(uuid.uuid4())
            
            # Create queue event
            queue_event = {
                'event_id': event_id,
                'account_id': account_id,
                'data': event_data,
                'times_queued': 1,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Add to queue and tracking set atomically
            pipe = self.redis.pipeline()
            pipe.sadd("active_events", deduplication_key)
            pipe.lpush("rebalance_queue", json.dumps(queue_event))
            pipe.execute()
            
            logger.info(f"Event queued successfully", extra={
                'event_id': event_id, 
                'account_id': account_id,
                'exec_command': exec_command,
                'deduplication_key': deduplication_key
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
    
    def get_active_events(self) -> set:
        """Get set of currently active event keys (account_id:exec_command)"""
        try:
            return self.redis.smembers("active_events")
        except Exception as e:
            logger.error(f"Failed to get active events: {e}")
            return set()
    
    def get_queued_accounts(self) -> set:
        """Get set of currently queued account IDs (legacy compatibility)"""
        try:
            active_events = self.redis.smembers("active_events")
            # Extract account IDs from account_id:exec_command keys
            accounts = set()
            for event_key in active_events:
                if ':' in event_key:
                    account_id = event_key.split(':', 1)[0]
                    accounts.add(account_id)
            return accounts
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