"""
Redis Queue Service for Event Broker
Handles all queue-related Redis operations
"""
import json
import uuid
from typing import Dict, Any, Optional, Set
from datetime import datetime
from app.services.base_redis_service import BaseRedisService
from app.models.event_data import EventData
from app.exceptions import EventDeduplicationError
from app.config import config
from app.logger import setup_logger

logger = setup_logger(__name__, level=config.LOG_LEVEL)


class RedisQueueService(BaseRedisService):
    """Service for queue operations in Redis"""
    
    def __init__(self, redis_url: str):
        """Initialize Redis Queue Service"""
        super().__init__(redis_url=redis_url)
    
    def enqueue_event(self, account_id: str, exec_command: str, event_data_dict: Dict[str, Any]) -> Optional[str]:
        """
        Enqueue a rebalance event if not already queued
        
        Args:
            account_id: Account identifier
            exec_command: Command to execute
            event_data_dict: Event payload data
            
        Returns:
            Event ID if enqueued, None if already queued
            
        Raises:
            EventDeduplicationError: If event is already queued
        """
        try:
            deduplication_key = f"{account_id}:{exec_command}"
            
            # Check if already active
            if self.is_event_active(account_id, exec_command):
                logger.info(f"Account {account_id} with command {exec_command} already queued, skipping duplicate event")
                raise EventDeduplicationError(f"Event {deduplication_key} already active")
            
            # Generate event ID if not provided
            event_id = event_data_dict.get('eventId', str(uuid.uuid4()))
            
            # Create EventData model for validation
            event_model = EventData(
                event_id=event_id,
                account_id=account_id,
                exec_command=exec_command,
                times_queued=1,
                created_at=datetime.now(),
                data=event_data_dict
            )
            
            # Convert to Redis format
            queue_event = event_model.to_redis_dict()
            
            # Add to queue and tracking set atomically
            def atomic_enqueue(client):
                pipe = client.pipeline()
                pipe.sadd("active_events_set", deduplication_key)
                pipe.lpush("rebalance_queue", json.dumps(queue_event))
                return pipe.execute()
            
            self.execute_with_retry(atomic_enqueue)
            
            logger.info(f"Event queued successfully", extra={
                'event_id': event_id,
                'account_id': account_id,
                'exec_command': exec_command,
                'deduplication_key': deduplication_key
            })
            
            return event_id
            
        except EventDeduplicationError:
            raise
        except Exception as e:
            logger.error(f"Failed to enqueue event for account {account_id}: {e}")
            raise
    
    def is_event_active(self, account_id: str, exec_command: str) -> bool:
        """
        Check if an event is already active
        
        Args:
            account_id: Account identifier  
            exec_command: Command to check
            
        Returns:
            True if event is active, False otherwise
        """
        try:
            deduplication_key = f"{account_id}:{exec_command}"
            
            def check_member(client):
                return client.sismember("active_events_set", deduplication_key)
            
            return self.execute_with_retry(check_member)
        except Exception as e:
            logger.error(f"Failed to check active event status: {e}")
            return False
    
    def get_queue_length(self) -> int:
        """Get current queue length"""
        try:
            def get_length(client):
                return client.llen("rebalance_queue")
            
            return self.execute_with_retry(get_length)
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0
    
    def get_active_events(self) -> Set[str]:
        """Get set of currently active event keys"""
        try:
            def get_members(client):
                return client.smembers("active_events_set")
            
            return self.execute_with_retry(get_members)
        except Exception as e:
            logger.error(f"Failed to get active events: {e}")
            return set()
    
    def get_queued_accounts(self) -> Set[str]:
        """Get set of currently queued account IDs"""
        try:
            active_events = self.get_active_events()
            accounts = set()
            for event_key in active_events:
                if ':' in event_key:
                    account_id = event_key.split(':', 1)[0]
                    accounts.add(account_id)
            return accounts
        except Exception as e:
            logger.error(f"Failed to get queued accounts: {e}")
            return set()