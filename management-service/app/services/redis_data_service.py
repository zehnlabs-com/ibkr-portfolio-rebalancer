"""
Redis Data Service for Management Service
Centralizes all Redis operations for the management-service
Uses strongly typed data models for type safety and validation
"""
import json
import uuid
import logging
import redis.asyncio as redis
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime, timedelta

# Import strongly typed models (local copies)
from app.models.account_data import AccountData, DashboardSummary
from app.models.event_data import EventData
from app.models.notification_data import NotificationData
from app.models.queue_data import QueueEventSummary

logger = logging.getLogger(__name__)


class RedisDataService:
    """Centralized Redis data access service for management-service"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            await self.redis_client.ping()
            logger.info(f"RedisDataService connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("RedisDataService disconnected from Redis")
    
    def _ensure_connected(self):
        """Ensure Redis client is connected"""
        if not self.redis_client:
            raise RuntimeError("Redis connection not established")
    
    # ========== Queue Operations ==========
    
    async def get_queue_length(self) -> int:
        """Get current queue length"""
        self._ensure_connected()
        return await self.redis_client.llen("rebalance_queue")
    
    async def get_active_events_count(self) -> int:
        """Get count of active events"""
        self._ensure_connected()
        return await self.redis_client.scard("active_events_set")
    
    async def get_queue_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from main queue"""
        self._ensure_connected()
        
        try:
            # Get events from queue
            raw_events = await self.redis_client.lrange("rebalance_queue", 0, limit - 1)
            
            events = []
            for event_json in raw_events:
                try:
                    event_data = json.loads(event_json)
                    
                    events.append({
                        "event_id": event_data.get("event_id", "unknown"),
                        "account_id": event_data.get("account_id", "unknown"),
                        "exec_command": event_data.get("exec", "unknown"),
                        "times_queued": event_data.get("times_queued", 1),
                        "created_at": event_data.get("created_at", "unknown"),
                        "data": event_data.get("data", {})
                    })
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse event JSON: {e}")
                    continue
            
            return events
        except Exception as e:
            logger.error(f"Failed to get queue events: {e}")
            raise
    
    async def get_retry_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from retry queue"""
        self._ensure_connected()
        
        try:
            # Get events from retry set
            raw_events = await self.redis_client.zrange("rebalance_retry_set", 0, limit - 1)
            
            events = []
            for event_json in raw_events:
                try:
                    event_data = json.loads(event_json)
                    
                    # Get the score (timestamp when added to retry queue)
                    score = await self.redis_client.zscore("rebalance_retry_set", event_json)
                    retry_after = None
                    if score:
                        # Add retry delay to the score to get when it will be retried
                        retry_after = datetime.fromtimestamp(score + 300).isoformat()  # 300 seconds delay
                    
                    events.append({
                        "event_id": event_data.get("event_id", "unknown"),
                        "account_id": event_data.get("account_id", "unknown"),
                        "exec_command": event_data.get("exec", "unknown"),
                        "times_queued": event_data.get("times_queued", 1),
                        "created_at": event_data.get("created_at", "unknown"),
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
    
    async def get_delayed_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from delayed execution queue"""
        self._ensure_connected()
        
        try:
            # Get events from delayed set
            events_with_scores = await self.redis_client.zrange(
                "delayed_execution_set", 
                0, 
                limit - 1, 
                withscores=True
            )
            
            events = []
            for event_json, score in events_with_scores:
                try:
                    event_data = json.loads(event_json)
                    
                    # Convert score (execution timestamp) to readable time
                    execution_time = datetime.fromtimestamp(score).isoformat()
                    
                    events.append({
                        "event_id": event_data.get("event_id", "unknown"),
                        "account_id": event_data.get("account_id", "unknown"),
                        "exec_command": event_data.get("exec", "unknown"),
                        "times_queued": event_data.get("times_queued", 1),
                        "created_at": event_data.get("created_at", "unknown"),
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
    
    async def remove_event(self, event_id: str) -> bool:
        """Remove specific event from all queues by event ID"""
        self._ensure_connected()
        
        try:
            # Search and remove from active queue
            raw_events = await self.redis_client.lrange("rebalance_queue", 0, -1)
            
            for event_json in raw_events:
                try:
                    event_data = json.loads(event_json)
                    if event_data.get("event_id") == event_id:
                        # Remove from queue and active events set
                        await self.redis_client.lrem("rebalance_queue", 1, event_json)
                        
                        account_id = event_data.get("account_id", "unknown")
                        exec_command = event_data.get("exec", "unknown")
                        deduplication_key = f"{account_id}:{exec_command}"
                        await self.redis_client.srem("active_events_set", deduplication_key)
                        
                        logger.info(f"Removed event {event_id} from active queue")
                        return True
                except json.JSONDecodeError:
                    continue
            
            # Search and remove from retry queue
            retry_events = await self.redis_client.zrange("rebalance_retry_set", 0, -1)
            
            for event_json in retry_events:
                try:
                    event_data = json.loads(event_json)
                    if event_data.get("event_id") == event_id:
                        await self.redis_client.zrem("rebalance_retry_set", event_json)
                        logger.info(f"Removed event {event_id} from retry queue")
                        return True
                except json.JSONDecodeError:
                    continue
            
            # Search and remove from delayed execution queue
            delayed_events = await self.redis_client.zrange("delayed_execution_set", 0, -1)
            
            for event_json in delayed_events:
                try:
                    event_data = json.loads(event_json)
                    if event_data.get("event_id") == event_id:
                        await self.redis_client.zrem("delayed_execution_set", event_json)
                        logger.info(f"Removed event {event_id} from delayed queue")
                        return True
                except json.JSONDecodeError:
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Failed to remove event {event_id}: {e}")
            raise
    
    async def add_manual_event(self, account_id: str, exec_command: str, data: Dict[str, Any]) -> str:
        """Add event to queue manually"""
        self._ensure_connected()
        
        try:
            # Create deduplication key
            deduplication_key = f"{account_id}:{exec_command}"
            
            # Check if already active
            if await self.redis_client.sismember("active_events_set", deduplication_key):
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
            pipe = self.redis_client.pipeline()
            pipe.sadd("active_events_set", deduplication_key)
            pipe.lpush("rebalance_queue", json.dumps(event_data))
            await pipe.execute()
            
            logger.info(f"Added manual event {event_id} to queue", extra={
                "event_id": event_id,
                "account_id": account_id,
                "exec_command": exec_command,
                "deduplication_key": deduplication_key
            })
            
            return event_id
        except Exception as e:
            logger.error(f"Failed to add manual event: {e}")
            raise
    
    async def clear_all_queues(self) -> Dict[str, int]:
        """Clear all events from all queues"""
        self._ensure_connected()
        
        try:
            # Get current counts before clearing
            active_count = await self.redis_client.llen("rebalance_queue")
            retry_count = await self.redis_client.zcard("rebalance_retry_set")
            delayed_count = await self.redis_client.zcard("delayed_execution_set")
            active_events_count = await self.redis_client.scard("active_events_set")
            
            # Clear all queues atomically
            pipe = self.redis_client.pipeline()
            pipe.delete("rebalance_queue")
            pipe.delete("rebalance_retry_set")
            pipe.delete("delayed_execution_set")
            pipe.delete("active_events_set")
            await pipe.execute()
            
            cleared_counts = {
                "active_queue": active_count,
                "retry_queue": retry_count,
                "delayed_queue": delayed_count,
                "active_events_set": active_events_count
            }
            
            logger.info(f"Cleared all queues", extra={"cleared_counts": cleared_counts})
            
            return cleared_counts
        except Exception as e:
            logger.error(f"Failed to clear all queues: {e}")
            raise
    
    async def get_active_events(self) -> List[str]:
        """Get active event keys"""
        self._ensure_connected()
        
        try:
            return list(await self.redis_client.smembers("active_events_set"))
        except Exception as e:
            logger.error(f"Failed to get active events: {e}")
            raise
    
    async def get_oldest_event_age(self) -> Optional[int]:
        """Get age of oldest event in seconds"""
        self._ensure_connected()
        
        try:
            # Get oldest event (from right end of queue)
            raw_events = await self.redis_client.lrange("rebalance_queue", -1, -1)
            
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
        self._ensure_connected()
        
        try:
            return await self.redis_client.zcard("rebalance_retry_set")
        except Exception as e:
            logger.warning(f"Failed to get retry events count: {e}")
            return 0
    
    async def get_delayed_events_count(self) -> int:
        """Get count of delayed events"""
        self._ensure_connected()
        
        try:
            return await self.redis_client.zcard("delayed_execution_set")
        except Exception as e:
            logger.warning(f"Failed to get delayed events count: {e}")
            return 0
    
    # ========== Account Data Operations ==========
    
    async def get_all_accounts_data(self) -> List[AccountData]:
        """Get all account data from Redis"""
        self._ensure_connected()
        
        try:
            # Get all account:* keys
            keys = await self.redis_client.keys("account:*")
            
            if not keys:
                return []
            
            # Get all account data at once
            account_data_strings = await self.redis_client.mget(keys)
            
            accounts_data = []
            for i, data_str in enumerate(account_data_strings):
                if data_str:
                    try:
                        account_data_dict = json.loads(data_str)
                        account_data = AccountData.from_dict(account_data_dict)
                        accounts_data.append(account_data)
                    except Exception as e:
                        # Log error but continue with other accounts
                        account_id = keys[i].split(':')[1] if ':' in keys[i] else 'unknown'
                        logger.error(f"Failed to parse account data for {account_id}: {e}")
            
            return accounts_data
            
        except Exception as e:
            logger.error(f"Failed to get all accounts data: {e}")
            raise
    
    async def get_account_data(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get specific account data"""
        self._ensure_connected()
        
        try:
            data = await self.redis_client.get(f"account:{account_id}")
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Failed to get account data for {account_id}: {e}")
            return None
    
    async def subscribe_to_updates(self) -> AsyncIterator[Dict[str, Any]]:
        """Subscribe to real-time dashboard updates"""
        self._ensure_connected()
        
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe("dashboard_updates")
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        yield data
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse dashboard update: {e}")
                        continue
        except Exception as e:
            logger.error(f"Failed to subscribe to updates: {e}")
            raise
    
    # ========== Notification Operations ==========
    
    async def get_notifications(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get notifications from the notification queue"""
        self._ensure_connected()
        
        try:
            # Get notifications (most recent first)
            notifications_data = await self.redis_client.zrevrange(
                'user_notifications', 
                0, 
                limit - 1
            )
            
            notifications = []
            for notification_json in notifications_data:
                try:
                    notification = json.loads(notification_json)
                    notifications.append(notification)
                except json.JSONDecodeError:
                    continue
            
            return notifications
        except Exception as e:
            logger.error(f"Failed to get notifications: {e}")
            return []
    
    async def get_notifications_count(self) -> int:
        """Get total count of notifications"""
        self._ensure_connected()
        
        try:
            return await self.redis_client.zcard('user_notifications')
        except Exception as e:
            logger.error(f"Failed to get notifications count: {e}")
            return 0
    
    async def get_unread_notifications_count(self) -> int:
        """Get count of unread notifications"""
        self._ensure_connected()
        
        try:
            count = await self.redis_client.get('user_notifications:unread_count')
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Failed to get unread notifications count: {e}")
            return 0
    
    async def mark_notification_read(self, notification_id: str) -> bool:
        """Mark a specific notification as read"""
        self._ensure_connected()
        
        try:
            # Get all notifications to find the one to mark as read
            all_notifications = await self.redis_client.zrange('user_notifications', 0, -1, withscores=True)
            
            for notification_json, score in all_notifications:
                try:
                    notification = json.loads(notification_json)
                    if notification.get('id') == notification_id and notification.get('status') != 'read':
                        # Update notification status
                        notification['status'] = 'read'
                        updated_json = json.dumps(notification)
                        
                        # Update in Redis
                        pipe = self.redis_client.pipeline()
                        pipe.zrem('user_notifications', notification_json)
                        pipe.zadd('user_notifications', {updated_json: score})
                        pipe.decr('user_notifications:unread_count')
                        await pipe.execute()
                        
                        logger.info(f"Marked notification {notification_id} as read")
                        return True
                except json.JSONDecodeError:
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {e}")
            return False
    
    async def mark_all_notifications_read(self) -> int:
        """Mark all notifications as read"""
        self._ensure_connected()
        
        try:
            # Get all unread notifications
            all_notifications = await self.redis_client.zrange('user_notifications', 0, -1, withscores=True)
            
            marked_count = 0
            pipe = self.redis_client.pipeline()
            
            for notification_json, score in all_notifications:
                try:
                    notification = json.loads(notification_json)
                    if notification.get('status') != 'read':
                        # Update notification status
                        notification['status'] = 'read'
                        updated_json = json.dumps(notification)
                        
                        # Queue update
                        pipe.zrem('user_notifications', notification_json)
                        pipe.zadd('user_notifications', {updated_json: score})
                        marked_count += 1
                except json.JSONDecodeError:
                    continue
            
            if marked_count > 0:
                # Reset unread counter
                pipe.set('user_notifications:unread_count', 0)
                await pipe.execute()
                
                logger.info(f"Marked {marked_count} notifications as read")
            
            return marked_count
        except Exception as e:
            logger.error(f"Failed to mark all notifications as read: {e}")
            return 0
    
    async def delete_notification(self, notification_id: str) -> bool:
        """Delete a specific notification"""
        self._ensure_connected()
        
        try:
            # Get all notifications to find the one to delete
            all_notifications = await self.redis_client.zrange('user_notifications', 0, -1)
            
            for notification_json in all_notifications:
                try:
                    notification = json.loads(notification_json)
                    if notification.get('id') == notification_id:
                        # Delete notification
                        pipe = self.redis_client.pipeline()
                        pipe.zrem('user_notifications', notification_json)
                        
                        # Decrement unread count if it was unread
                        if notification.get('status') != 'read':
                            pipe.decr('user_notifications:unread_count')
                        
                        await pipe.execute()
                        
                        logger.info(f"Deleted notification {notification_id}")
                        return True
                except json.JSONDecodeError:
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Failed to delete notification: {e}")
            return False
    
    async def monitor_new_notifications(self, last_timestamp: float) -> List[Dict[str, Any]]:
        """Get new notifications since timestamp"""
        self._ensure_connected()
        
        try:
            # Get notifications newer than the timestamp
            new_notifications = await self.redis_client.zrangebyscore(
                'user_notifications',
                last_timestamp,
                '+inf',
                withscores=True
            )
            
            notifications = []
            for notification_json, score in new_notifications:
                try:
                    notification = json.loads(notification_json)
                    notification['timestamp_score'] = score
                    notifications.append(notification)
                except json.JSONDecodeError:
                    continue
            
            return notifications
        except Exception as e:
            logger.error(f"Failed to monitor new notifications: {e}")
            return []
    
    # ========== Health Operations ==========
    
    async def get_problematic_events(self, min_retries: int = 2) -> List[Dict[str, Any]]:
        """Get events that have been retried multiple times"""
        self._ensure_connected()
        
        try:
            raw_events = await self.redis_client.lrange("rebalance_queue", 0, -1)
            
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