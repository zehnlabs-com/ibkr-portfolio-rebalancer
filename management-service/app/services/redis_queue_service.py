"""
Redis Queue Service for Management Service
Handles all queue-related operations in Redis
"""
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.services.base_redis_service import BaseRedisService
from app.models.event_data import EventData
from app.models.queue_data import QueueEventSummary

logger = logging.getLogger(__name__)


class RedisQueueService(BaseRedisService):
    """Service for queue operations in Redis"""
    
    def __init__(self, redis_url: str):
        """Initialize Redis Queue Service"""
        super().__init__(redis_url)
    
    async def get_queue_length(self) -> int:
        """Get current queue length"""
        try:
            async def get_length(client):
                return await client.llen("rebalance_events")
            
            length = await self.execute_with_retry(get_length)
            return length or 0
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0
    
    async def get_active_events_count(self) -> int:
        """Get count of active events"""
        try:
            async def get_count(client):
                return await client.scard("active_events_set")
            
            count = await self.execute_with_retry(get_count)
            return count or 0
        except Exception as e:
            logger.error(f"Failed to get active events count: {e}")
            return 0
    
    async def get_queue_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from main queue"""
        try:
            async def get_events(client):
                # Get events from main queue
                events = await client.lrange("rebalance_events", 0, limit - 1)
                parsed_events = []
                
                for event_json in events:
                    try:
                        event_data = json.loads(event_json)
                        # Convert to EventData if possible, otherwise use raw data
                        try:
                            event_obj = EventData.from_dict(event_data)
                            parsed_events.append(event_obj.to_dict())
                        except Exception:
                            # Fallback to raw data if EventData parsing fails
                            parsed_events.append(event_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in queue: {event_json}")
                        continue
                
                return parsed_events
            
            return await self.execute_with_retry(get_events)
        except Exception as e:
            logger.error(f"Failed to get queue events: {e}")
            return []
    
    async def get_retry_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from retry queue"""
        try:
            async def get_retry_events(client):
                # Get events from retry queue (sorted set)
                events = await client.zrange("retry_events", 0, limit - 1, withscores=True)
                parsed_events = []
                
                for event_json, score in events:
                    try:
                        event_data = json.loads(event_json)
                        # Add retry time information
                        event_data['retry_after'] = datetime.fromtimestamp(score).isoformat()
                        
                        try:
                            event_obj = EventData.from_dict(event_data)
                            parsed_events.append(event_obj.to_dict())
                        except Exception:
                            parsed_events.append(event_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in retry queue: {event_json}")
                        continue
                
                return parsed_events
            
            return await self.execute_with_retry(get_retry_events)
        except Exception as e:
            logger.error(f"Failed to get retry events: {e}")
            return []
    
    async def get_delayed_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from delayed execution queue"""
        try:
            async def get_delayed_events(client):
                # Get events from delayed queue (sorted set)
                events = await client.zrange("delayed_events", 0, limit - 1, withscores=True)
                parsed_events = []
                
                for event_json, score in events:
                    try:
                        event_data = json.loads(event_json)
                        # Add execution time information
                        event_data['execute_at'] = datetime.fromtimestamp(score).isoformat()
                        
                        try:
                            event_obj = EventData.from_dict(event_data)
                            parsed_events.append(event_obj.to_dict())
                        except Exception:
                            parsed_events.append(event_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in delayed queue: {event_json}")
                        continue
                
                return parsed_events
            
            return await self.execute_with_retry(get_delayed_events)
        except Exception as e:
            logger.error(f"Failed to get delayed events: {e}")
            return []
    
    async def remove_event(self, event_id: str) -> bool:
        """Remove event from all queues"""
        try:
            async def remove_from_queues(client):
                removed_count = 0
                
                # Get all events from main queue and find matching event
                events = await client.lrange("rebalance_events", 0, -1)
                for i, event_json in enumerate(events):
                    try:
                        event_data = json.loads(event_json)
                        if event_data.get('event_id') == event_id:
                            # Remove from list by value
                            removed = await client.lrem("rebalance_events", 1, event_json)
                            removed_count += removed
                            break
                    except json.JSONDecodeError:
                        continue
                
                # Remove from retry queue
                retry_events = await client.zrange("retry_events", 0, -1)
                for event_json in retry_events:
                    try:
                        event_data = json.loads(event_json)
                        if event_data.get('event_id') == event_id:
                            removed = await client.zrem("retry_events", event_json)
                            removed_count += removed
                            break
                    except json.JSONDecodeError:
                        continue
                
                # Remove from delayed queue
                delayed_events = await client.zrange("delayed_events", 0, -1)
                for event_json in delayed_events:
                    try:
                        event_data = json.loads(event_json)
                        if event_data.get('event_id') == event_id:
                            removed = await client.zrem("delayed_events", event_json)
                            removed_count += removed
                            break
                    except json.JSONDecodeError:
                        continue
                
                # Remove from active events set
                await client.srem("active_events_set", f"{event_data.get('account_id', '')}:{event_data.get('exec_command', '')}")
                
                return removed_count > 0
            
            return await self.execute_with_retry(remove_from_queues)
        except Exception as e:
            logger.error(f"Failed to remove event {event_id}: {e}")
            return False
    
    async def add_manual_event(self, account_id: str, exec_command: str, data: Dict[str, Any]) -> str:
        """Add a manual event to the queue"""
        try:
            async def add_event(client):
                # Create event data
                event_id = str(uuid.uuid4())
                event_data = {
                    'event_id': event_id,
                    'account_id': account_id,
                    'exec_command': exec_command,
                    'created_at': datetime.now().isoformat(),
                    'source': 'manual',
                    'times_queued': 1,
                    **data
                }
                
                # Add to main queue
                await client.lpush("rebalance_events", json.dumps(event_data))
                
                # Add to active events set
                await client.sadd("active_events_set", f"{account_id}:{exec_command}")
                
                return event_id
            
            return await self.execute_with_retry(add_event)
        except Exception as e:
            logger.error(f"Failed to add manual event: {e}")
            raise
    
    async def clear_all_queues(self) -> Dict[str, int]:
        """Clear all event queues"""
        try:
            async def clear_queues(client):
                pipe = client.pipeline()
                
                # Count events before clearing
                main_count = await client.llen("rebalance_events") or 0
                retry_count = await client.zcard("retry_events") or 0
                delayed_count = await client.zcard("delayed_events") or 0
                active_count = await client.scard("active_events_set") or 0
                
                # Clear all queues
                pipe.delete("rebalance_events")
                pipe.delete("retry_events")
                pipe.delete("delayed_events")
                pipe.delete("active_events_set")
                
                await pipe.execute()
                
                return {
                    'main_queue': main_count,
                    'retry_queue': retry_count,
                    'delayed_queue': delayed_count,
                    'active_events': active_count
                }
            
            return await self.execute_with_retry(clear_queues)
        except Exception as e:
            logger.error(f"Failed to clear queues: {e}")
            return {'main_queue': 0, 'retry_queue': 0, 'delayed_queue': 0, 'active_events': 0}
    
    async def get_active_events(self) -> List[str]:
        """Get list of active events"""
        try:
            async def get_active(client):
                events = await client.smembers("active_events_set")
                return list(events) if events else []
            
            return await self.execute_with_retry(get_active)
        except Exception as e:
            logger.error(f"Failed to get active events: {e}")
            return []
    
    async def get_oldest_event_age(self) -> Optional[int]:
        """Get age of oldest event in seconds"""
        try:
            async def get_oldest_age(client):
                # Check main queue
                events = await client.lrange("rebalance_events", -1, -1)
                if events:
                    try:
                        event_data = json.loads(events[0])
                        created_at = datetime.fromisoformat(event_data.get('created_at', ''))
                        age = (datetime.now() - created_at).total_seconds()
                        return int(age)
                    except (json.JSONDecodeError, ValueError):
                        pass
                
                return None
            
            return await self.execute_with_retry(get_oldest_age)
        except Exception as e:
            logger.error(f"Failed to get oldest event age: {e}")
            return None
    
    async def get_retry_events_count(self) -> int:
        """Get count of events in retry queue"""
        try:
            async def get_count(client):
                return await client.zcard("retry_events")
            
            count = await self.execute_with_retry(get_count)
            return count or 0
        except Exception as e:
            logger.error(f"Failed to get retry events count: {e}")
            return 0
    
    async def get_delayed_events_count(self) -> int:
        """Get count of events in delayed queue"""
        try:
            async def get_count(client):
                return await client.zcard("delayed_events")
            
            count = await self.execute_with_retry(get_count)
            return count or 0
        except Exception as e:
            logger.error(f"Failed to get delayed events count: {e}")
            return 0
    
    async def get_problematic_events(self, min_retries: int = 2) -> List[Dict[str, Any]]:
        """Get events that have been retried multiple times"""
        try:
            async def get_problematic(client):
                # Check all queues for events with high retry count
                problematic_events = []
                
                # Check main queue
                events = await client.lrange("rebalance_events", 0, -1)
                for event_json in events:
                    try:
                        event_data = json.loads(event_json)
                        if event_data.get('times_queued', 0) >= min_retries:
                            problematic_events.append(event_data)
                    except json.JSONDecodeError:
                        continue
                
                # Check retry queue
                retry_events = await client.zrange("retry_events", 0, -1)
                for event_json in retry_events:
                    try:
                        event_data = json.loads(event_json)
                        if event_data.get('times_queued', 0) >= min_retries:
                            problematic_events.append(event_data)
                    except json.JSONDecodeError:
                        continue
                
                return problematic_events
            
            return await self.execute_with_retry(get_problematic)
        except Exception as e:
            logger.error(f"Failed to get problematic events: {e}")
            return []