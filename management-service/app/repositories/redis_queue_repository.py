"""
Redis implementation of queue repository
"""
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import redis.asyncio as redis

from app.repositories.interfaces import IQueueRepository

logger = logging.getLogger(__name__)


class RedisQueueRepository(IQueueRepository):
    """Redis implementation of queue repository"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        """Connect to Redis"""
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            await self.redis.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")
    
    async def get_queue_length(self) -> int:
        """Get current queue length"""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
        return await self.redis.llen("rebalance_queue")
    
    async def get_active_events_count(self) -> int:
        """Get count of active events"""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
        return await self.redis.scard("active_events_set")
    
    async def get_queue_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from queue"""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
            
        try:
            # Get events from queue (from right, which is the consuming end)
            raw_events = await self.redis.lrange("rebalance_queue", 0, limit - 1)
            
            events = []
            for event_json in raw_events:
                try:
                    event_data = json.loads(event_json)
                    
                    # Extract information
                    event_id = event_data.get("event_id", "unknown")
                    account_id = event_data.get("account_id", "unknown")
                    exec_command = event_data.get("exec", "unknown")
                    times_queued = event_data.get("times_queued", 1)
                    created_at = event_data.get("created_at", "unknown")
                    
                    events.append({
                        "event_id": event_id,
                        "account_id": account_id,
                        "exec_command": exec_command,
                        "times_queued": times_queued,
                        "created_at": created_at,
                        "data": event_data.get("data", {})
                    })
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse event JSON: {e}")
                    continue
            
            return events
        except Exception as e:
            logger.error(f"Failed to get queue events: {e}")
            raise
    
    async def remove_event(self, event_id: str) -> bool:
        """Remove specific event from queue by event ID (searches both active and retry queues)"""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
            
        try:
            # First try to remove from active queue
            raw_events = await self.redis.lrange("rebalance_queue", 0, -1)
            
            # Find and remove the event from active queue
            for event_json in raw_events:
                try:
                    event_data = json.loads(event_json)
                    if event_data.get("event_id") == event_id:
                        # Remove from queue using event content
                        await self.redis.lrem("rebalance_queue", 1, event_json)
                        
                        # Remove from active events set
                        account_id = event_data.get("account_id", "unknown")
                        exec_command = event_data.get("exec", "unknown")
                        deduplication_key = f"{account_id}:{exec_command}"
                        await self.redis.srem("active_events_set", deduplication_key)
                        
                        logger.info(f"Removed event {event_id} from active queue and active events")
                        return True
                except json.JSONDecodeError:
                    continue
            
            # If not found in active queue, try retry queue
            retry_events = await self.redis.zrange("rebalance_retry_set", 0, -1)
            
            for event_json in retry_events:
                try:
                    event_data = json.loads(event_json)
                    if event_data.get("event_id") == event_id:
                        # Remove from retry queue
                        await self.redis.zrem("rebalance_retry_set", event_json)
                        
                        logger.info(f"Removed event {event_id} from retry queue")
                        return True
                except json.JSONDecodeError:
                    continue
            
            # If not found in retry queue, try delayed execution queue
            delayed_events = await self.redis.zrange("delayed_execution_set", 0, -1)
            
            for event_json in delayed_events:
                try:
                    event_data = json.loads(event_json)
                    if event_data.get("event_id") == event_id:
                        # Remove from delayed execution queue
                        await self.redis.zrem("delayed_execution_set", event_json)
                        
                        logger.info(f"Removed event {event_id} from delayed execution queue")
                        return True
                except json.JSONDecodeError:
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Failed to remove event {event_id}: {e}")
            raise
    
    async def add_event(self, account_id: str, exec_command: str, data: Dict[str, Any]) -> str:
        """Add event to queue"""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
            
        try:
            # Create deduplication key
            deduplication_key = f"{account_id}:{exec_command}"
            
            # Check if already active
            if await self.redis.sismember("active_events_set", deduplication_key):
                raise ValueError(f"Event {deduplication_key} already active")
            
            # Generate event ID
            event_id = str(uuid.uuid4())
            
            # Create event data
            event_data = {
                "event_id": event_id,
                "account_id": account_id,
                "exec": exec_command,
                **data,
                "times_queued": 1,
                "created_at": datetime.now().isoformat()
            }
            
            # Add to queue and active events atomically
            pipe = self.redis.pipeline()
            pipe.sadd("active_events_set", deduplication_key)
            pipe.lpush("rebalance_queue", json.dumps(event_data))
            await pipe.execute()
            
            logger.info(f"Added event {event_id} to queue", extra={
                "event_id": event_id,
                "account_id": account_id,
                "exec_command": exec_command,
                "deduplication_key": deduplication_key
            })
            
            return event_id
        except Exception as e:
            logger.error(f"Failed to add event: {e}")
            raise
    
    async def get_active_events(self) -> List[str]:
        """Get active event keys"""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
            
        try:
            return list(await self.redis.smembers("active_events_set"))
        except Exception as e:
            logger.error(f"Failed to get active events: {e}")
            raise
    
    async def count_events_with_retries(self) -> int:
        """Count events with times_queued > 1"""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
            
        try:
            # Get all events from queue
            raw_events = await self.redis.lrange("rebalance_queue", 0, -1)
            
            count = 0
            for event_json in raw_events:
                try:
                    event_data = json.loads(event_json)
                    times_queued = event_data.get("times_queued", 1)
                    if times_queued > 1:
                        count += 1
                except json.JSONDecodeError:
                    continue
            
            return count
        except Exception as e:
            logger.warning(f"Failed to count events with retries: {e}")
            return 0
    
    async def get_oldest_event_age(self) -> Optional[int]:
        """Get age of oldest event in seconds"""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
            
        try:
            # Get oldest event (from right end of queue)
            raw_events = await self.redis.lrange("rebalance_queue", -1, -1)
            
            if not raw_events:
                return None
            
            event_data = json.loads(raw_events[0])
            created_at_str = event_data.get("created_at")
            
            if not created_at_str:
                return None
            
            # Parse timestamp
            created_at = datetime.fromisoformat(created_at_str.replace('Z', ''))
            now = datetime.now()
            
            age_seconds = int((now - created_at).total_seconds())
            return age_seconds
        except Exception as e:
            logger.warning(f"Failed to get oldest event age: {e}")
            return None
    
    async def get_retry_events_count(self) -> int:
        """Get count of retry events"""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
            
        try:
            return await self.redis.zcard("rebalance_retry_set")
        except Exception as e:
            logger.warning(f"Failed to get retry events count: {e}")
            return 0
    
    async def get_retry_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from retry queue"""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
            
        try:
            # Get events from retry set (sorted by timestamp)
            raw_events = await self.redis.zrange("rebalance_retry_set", 0, limit - 1)
            
            events = []
            for event_json in raw_events:
                try:
                    event_data = json.loads(event_json)
                    
                    # Extract information
                    event_id = event_data.get("event_id", "unknown")
                    account_id = event_data.get("account_id", "unknown")
                    exec_command = event_data.get("exec", "unknown")
                    times_queued = event_data.get("times_queued", 1)
                    created_at = event_data.get("created_at", "unknown")
                    
                    # Get the score (timestamp when added to retry queue)
                    score = await self.redis.zscore("rebalance_retry_set", event_json)
                    retry_after = None
                    if score:
                        # Add retry delay to the score to get when it will be retried
                        retry_after = datetime.fromtimestamp(score + 300).isoformat()  # 300 seconds delay
                    
                    events.append({
                        "event_id": event_id,
                        "account_id": account_id,
                        "exec_command": exec_command,
                        "times_queued": times_queued,
                        "created_at": created_at,
                        "retry_after": retry_after,
                        "data": event_data.get("data", {})
                    })
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse retry event JSON: {e}")
                    continue
            
            return events
        except Exception as e:
            logger.error(f"Failed to get retry events: {e}")
            raise
    
    async def get_delayed_events_count(self) -> int:
        """Get count of delayed events"""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
            
        try:
            return await self.redis.zcard("delayed_execution_set")
        except Exception as e:
            logger.warning(f"Failed to get delayed events count: {e}")
            return 0
    
    async def get_delayed_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from delayed execution queue"""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
            
        try:
            # Get events from delayed set (sorted by execution timestamp)
            events_with_scores = await self.redis.zrange(
                "delayed_execution_set", 
                0, 
                limit - 1, 
                withscores=True
            )
            
            events = []
            for event_json, score in events_with_scores:
                try:
                    event_data = json.loads(event_json)
                    
                    # Extract information
                    event_id = event_data.get("event_id", "unknown")
                    account_id = event_data.get("account_id", "unknown")
                    exec_command = event_data.get("exec", "unknown")
                    times_queued = event_data.get("times_queued", 1)
                    created_at = event_data.get("created_at", "unknown")
                    
                    # Convert score (execution timestamp) to readable time
                    execution_time = datetime.fromtimestamp(score).isoformat()
                    
                    events.append({
                        "event_id": event_id,
                        "account_id": account_id,
                        "exec_command": exec_command,
                        "times_queued": times_queued,
                        "created_at": created_at,
                        "execution_time": execution_time,
                        "data": event_data.get("data", {})
                    })
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse delayed event JSON: {e}")
                    continue
            
            return events
        except Exception as e:
            logger.error(f"Failed to get delayed events: {e}")
            raise