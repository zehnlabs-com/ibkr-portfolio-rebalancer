"""
Redis implementation of health repository
"""
import json
import logging
from typing import Dict, Any, List, Optional
import redis.asyncio as redis

from app.repositories.interfaces import IHealthRepository

logger = logging.getLogger(__name__)


class RedisHealthRepository(IHealthRepository):
    """Redis implementation of health repository"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        """Connect to Redis"""
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            await self.redis.ping()
            logger.info(f"HealthRepository connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("HealthRepository disconnected from Redis")
    
    
    async def get_problematic_events(self, min_retries: int = 2) -> List[Dict[str, Any]]:
        """Get events that have been retried multiple times"""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
            
        try:
            raw_events = await self.redis.lrange("rebalance_queue", 0, -1)
            
            problematic_events = []
            
            for event_json in raw_events:
                try:
                    event_data = json.loads(event_json)
                    times_queued = event_data.get("times_queued", 1)
                    
                    if times_queued >= min_retries:
                        problematic_events.append({
                            "event_id": event_data.get("event_id", "unknown"),
                            "account_id": event_data.get("account_id", "unknown"),
                            "exec_command": event_data.get("exec", "unknown"),
                            "times_queued": times_queued,
                            "created_at": event_data.get("created_at", "unknown"),
                            "data": event_data.get("data", {})
                        })
                except json.JSONDecodeError:
                    continue
            
            return problematic_events
        except Exception as e:
            logger.error(f"Failed to get problematic events: {e}")
            return []