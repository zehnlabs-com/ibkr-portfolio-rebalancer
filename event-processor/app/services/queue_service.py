"""
Redis Queue Service for Event Processor
"""
from typing import Optional
from app.services.redis_queue_service import RedisQueueService
from app.models.events import EventInfo
from app.logger import AppLogger

app_logger = AppLogger(__name__)


class QueueService:
    """Redis queue service for consuming rebalance events"""
    
    def __init__(self, redis_queue_service: RedisQueueService = None, user_notification_service=None):
        self.redis_queue_service = redis_queue_service or RedisQueueService()
        self.user_notification_service = user_notification_service
    
    async def get_next_event(self) -> Optional[EventInfo]:
        """
        Get next event from queue with timeout
        
        Returns:
            EventInfo: Event object if available, None if timeout
        """
        return await self.redis_queue_service.dequeue_event()
    
    async def remove_from_queued(self, account_id: str, exec_command: str = None):
        """Remove account+command from active events set"""
        await self.redis_queue_service.remove_from_active(account_id, exec_command)
    
    async def get_queue_length(self) -> int:
        """Get current queue length"""
        stats = await self.redis_queue_service.get_queue_stats()
        return stats.get('main_queue', 0)
    
    async def get_active_events(self) -> set:
        """Get set of currently active event keys (account_id:exec_command)"""
        stats = await self.redis_queue_service.get_queue_stats()
        return stats.get('active_events', set())
    
    async def get_queued_accounts(self) -> set:
        """Get set of currently queued account IDs (legacy compatibility)"""
        # This method reconstructs account IDs from active events
        # for backward compatibility
        stats = await self.redis_queue_service.get_queue_stats()
        active_events = stats.get('active_events', set())
        accounts = set()
        for event_key in active_events:
            if ':' in str(event_key):
                account_id = str(event_key).split(':', 1)[0]
                accounts.add(account_id)
        return accounts
    
    async def is_connected(self) -> bool:
        """Check if Redis connection is active"""
        return await self.redis_queue_service.is_connected()
    
    async def add_to_delayed_queue(self, event_info: EventInfo, next_execution_time) -> EventInfo:
        """
        Add event to delayed execution queue with specific execution time
        
        Args:
            event_info: Event to delay
            next_execution_time: When the event should be executed
            
        Returns:
            Updated EventInfo object
        """
        await self.redis_queue_service.move_to_delayed(event_info, next_execution_time)
        
        # Send delayed notification
        if self.user_notification_service:
            await self.user_notification_service.send_notification(
                event_info, 
                'event_delayed', 
                {'delayed_until': next_execution_time.strftime('%H:%M')}
            )
        
        return event_info
    
    
    async def process_delayed_events(self):
        """
        Process delayed events that are ready for execution
        Move ready events from delayed queue to main queue
        """
        count = await self.redis_queue_service.process_delayed_queue()
        if count > 0:
            app_logger.log_info(f"Processed {count} delayed events")
    
    async def get_delayed_events_count(self) -> int:
        """Get count of events in delayed execution queue"""
        stats = await self.redis_queue_service.get_queue_stats()
        return stats.get('delayed_queue', 0)
    
    
    async def recover_stuck_active_events(self) -> int:
        """
        Recover events stuck in active_events_set after service restart
        
        Returns:
            int: Number of events recovered
        """
        return await self.redis_queue_service.recover_stuck_events()
    
