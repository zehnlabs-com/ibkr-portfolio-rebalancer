"""
Redis implementation of health repository - thin wrapper around RedisDataService
"""
from typing import Dict, Any, List
from app.repositories.interfaces import IHealthRepository
from app.services.redis_data_service import RedisDataService


class RedisHealthRepository(IHealthRepository):
    """Redis implementation of health repository"""
    
    def __init__(self, redis_data_service: RedisDataService):
        self.redis_data_service = redis_data_service
    
    async def get_problematic_events(self, min_retries: int = 2) -> List[Dict[str, Any]]:
        """Get events that have been retried multiple times"""
        return await self.redis_data_service.get_problematic_events(min_retries)