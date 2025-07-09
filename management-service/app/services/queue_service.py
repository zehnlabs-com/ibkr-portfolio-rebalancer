"""
Queue service implementation
"""
import logging
from typing import Dict, Any, List

from app.services.interfaces import IQueueService
from app.repositories.interfaces import IQueueRepository

logger = logging.getLogger(__name__)


class QueueService(IQueueService):
    """Queue service implementation"""
    
    def __init__(self, queue_repository: IQueueRepository):
        self.queue_repository = queue_repository
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get comprehensive queue status"""
        try:
            # Get queue length
            queue_length = await self.queue_repository.get_queue_length()
            
            # Get active events count
            active_events_count = await self.queue_repository.get_active_events_count()
            
            # Get oldest event age
            oldest_event_age = await self.queue_repository.get_oldest_event_age()
            
            # Get events with retries count
            events_with_retries = await self.queue_repository.count_events_with_retries()
            
            return {
                "queue_length": queue_length,
                "active_events_count": active_events_count,
                "oldest_event_age_seconds": oldest_event_age,
                "events_with_retries": events_with_retries
            }
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            raise
    
    async def get_queue_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from queue with details"""
        try:
            return await self.queue_repository.get_queue_events(limit)
        except Exception as e:
            logger.error(f"Failed to get queue events: {e}")
            raise
    
    async def remove_event(self, event_id: str) -> bool:
        """Remove specific event from queue"""
        try:
            return await self.queue_repository.remove_event(event_id)
        except Exception as e:
            logger.error(f"Failed to remove event {event_id}: {e}")
            raise
    
    async def add_event(self, account_id: str, exec_command: str, data: Dict[str, Any]) -> str:
        """Add event to queue"""
        try:
            return await self.queue_repository.add_event(account_id, exec_command, data)
        except Exception as e:
            logger.error(f"Failed to add event: {e}")
            raise