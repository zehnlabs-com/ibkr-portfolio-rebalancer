"""
Redis implementation of queue repository - thin wrapper around RedisDataService
"""
from typing import Dict, Any, List
from app.repositories.interfaces import IQueueRepository
from app.services.redis_data_service import RedisDataService


class RedisQueueRepository(IQueueRepository):
    """Redis implementation of queue repository"""
    
    def __init__(self, redis_data_service: RedisDataService):
        self.redis_data_service = redis_data_service
    
    async def get_queue_length(self) -> int:
        """Get current queue length"""
        return await self.redis_data_service.get_queue_length()
    
    async def get_active_events_count(self) -> int:
        """Get count of active events"""
        return await self.redis_data_service.get_active_events_count()
    
    async def get_queue_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from queue"""
        return await self.redis_data_service.get_queue_events(limit)
    
    async def remove_event(self, event_id: str) -> bool:
        """Remove specific event from queue by event ID"""
        return await self.redis_data_service.remove_event(event_id)
    
    async def add_event(self, account_id: str, exec_command: str, data: Dict[str, Any]) -> str:
        """Add event to queue"""
        return await self.redis_data_service.add_manual_event(account_id, exec_command, data)
    
    async def get_active_events(self) -> List[str]:
        """Get active event keys"""
        return await self.redis_data_service.get_active_events()
    
    async def get_oldest_event_age(self) -> int:
        """Get age of oldest event in seconds"""
        return await self.redis_data_service.get_oldest_event_age()
    
    async def get_retry_events_count(self) -> int:
        """Get count of retry events"""
        return await self.redis_data_service.get_retry_events_count()
    
    async def get_retry_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from retry queue"""
        return await self.redis_data_service.get_retry_events(limit)
    
    async def get_delayed_events_count(self) -> int:
        """Get count of delayed events"""
        return await self.redis_data_service.get_delayed_events_count()
    
    async def get_delayed_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from delayed execution queue"""
        return await self.redis_data_service.get_delayed_events(limit)
    
    async def clear_all_queues(self) -> Dict[str, int]:
        """Clear all events from all queues and return counts of cleared events"""
        return await self.redis_data_service.clear_all_queues()
    
