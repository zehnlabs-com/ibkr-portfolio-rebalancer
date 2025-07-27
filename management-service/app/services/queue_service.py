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
            
            # Get retry events count
            retry_events_count = await self.queue_repository.get_retry_events_count()
            
            # Get delayed events count
            delayed_events_count = await self.queue_repository.get_delayed_events_count()
            
            # Get oldest event age
            oldest_event_age = await self.queue_repository.get_oldest_event_age()
            
            return {
                "queue_length": queue_length,
                "active_events_count": active_events_count,
                "retry_events_count": retry_events_count,
                "delayed_events_count": delayed_events_count,
                "oldest_event_age_seconds": oldest_event_age
            }
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            raise
    
    async def get_queue_events(self, limit: int = 100, event_type: str = None) -> List[Dict[str, Any]]:
        """Get events from queue with details and optional type filtering"""
        try:
            if event_type == "active":
                # Get only active events
                active_events = await self.queue_repository.get_queue_events(limit)
                for event in active_events:
                    event["type"] = "active"
                return active_events
            elif event_type == "retry":
                # Get only retry events
                retry_events = await self.queue_repository.get_retry_events(limit)
                for event in retry_events:
                    event["type"] = "retry"
                return retry_events
            elif event_type == "delayed":
                # Get only delayed events
                delayed_events = await self.queue_repository.get_delayed_events(limit)
                for event in delayed_events:
                    event["type"] = "delayed"
                return delayed_events
            else:
                # Get active, retry, and delayed events
                events_per_type = limit // 3
                active_events = await self.queue_repository.get_queue_events(events_per_type)
                retry_events = await self.queue_repository.get_retry_events(events_per_type)
                delayed_events = await self.queue_repository.get_delayed_events(events_per_type)
                
                # Add type field to each event
                for event in active_events:
                    event["type"] = "active"
                for event in retry_events:
                    event["type"] = "retry"
                for event in delayed_events:
                    event["type"] = "delayed"
                
                # Combine and sort by created_at or times_queued
                all_events = active_events + retry_events + delayed_events
                all_events.sort(key=lambda x: (x.get("times_queued", 1), x.get("created_at", "")), reverse=True)
                
                return all_events[:limit]
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
    
    async def clear_all_queues(self) -> Dict[str, int]:
        """Clear all events from all queues and return counts of cleared events"""
        try:
            return await self.queue_repository.clear_all_queues()
        except Exception as e:
            logger.error(f"Failed to clear all queues: {e}")
            raise