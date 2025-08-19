"""
Redis Queue Service for Event Broker
"""
from typing import Dict, Any, Optional
from app.services.redis_queue_service import RedisQueueService
from app.logger import setup_logger
from app.config import config

logger = setup_logger(__name__, level=config.LOG_LEVEL)


class QueueService:
    """Redis queue service for managing rebalance events"""
    
    def __init__(self, redis_queue_service=None):
        self.redis_queue_service = redis_queue_service or RedisQueueService()
        
    async def enqueue_event(self, account_id: str, event_data: Dict[str, Any]) -> Optional[str]:
        """
        Enqueue a rebalance event if account+command combination is not already queued
        
        Returns:
            str: event_id if enqueued, None if account+command already queued
        """
        # Extract command from event data - required field
        exec_command = event_data.get('exec')
        if not exec_command:
            logger.error(f"Event missing required 'exec' field for account {account_id}, skipping event", extra={
                'account_id': account_id,
                'event_data': event_data
            })
            return None
        
        # Use RedisQueueService to enqueue the event
        return self.redis_queue_service.enqueue_event(account_id, exec_command, event_data)
    
    def get_queue_length(self) -> int:
        """Get current queue length"""
        return self.redis_queue_service.get_queue_length()
    
    def get_active_events(self) -> set:
        """Get set of currently active event keys (account_id:exec_command)"""
        return self.redis_queue_service.get_active_events()
    
    def get_queued_accounts(self) -> set:
        """Get set of currently queued account IDs (legacy compatibility)"""
        return self.redis_queue_service.get_queued_accounts()
    
    def is_connected(self) -> bool:
        """Check if Redis connection is active"""
        return self.redis_queue_service.is_connected()