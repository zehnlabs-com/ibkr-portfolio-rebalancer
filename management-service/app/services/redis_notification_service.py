"""
Redis Notification Service for Management Service
Handles all notification operations in Redis
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.services.base_redis_service import BaseRedisService
from app.models.notification_data import NotificationData

logger = logging.getLogger(__name__)


class RedisNotificationService(BaseRedisService):
    """Service for notification operations in Redis"""
    
    def __init__(self, redis_url: str):
        """Initialize Redis Notification Service"""
        super().__init__(redis_url)
    
    async def get_notifications(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get notifications from Redis"""
        try:
            async def get_notifications_data(client):
                # Get notifications from sorted set (most recent first)
                notifications = await client.zrevrange("user_notifications", 0, limit - 1, withscores=True)
                parsed_notifications = []
                
                for notification_json, score in notifications:
                    try:
                        notification_data = json.loads(notification_json)
                        # Add timestamp from score
                        notification_data['timestamp'] = datetime.fromtimestamp(score).isoformat()
                        
                        try:
                            notification_obj = NotificationData.from_dict(notification_data)
                            parsed_notifications.append(notification_obj.to_dict())
                        except Exception:
                            # Fallback to raw data if NotificationData parsing fails
                            parsed_notifications.append(notification_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in notifications: {notification_json}")
                        continue
                
                return parsed_notifications
            
            return await self.execute_with_retry(get_notifications_data)
        except Exception as e:
            logger.error(f"Failed to get notifications: {e}")
            return []
    
    async def get_notifications_count(self) -> int:
        """Get total count of notifications"""
        try:
            async def get_count(client):
                return await client.zcard("user_notifications")
            
            count = await self.execute_with_retry(get_count)
            return count or 0
        except Exception as e:
            logger.error(f"Failed to get notifications count: {e}")
            return 0
    
    async def get_unread_notifications_count(self) -> int:
        """Get count of unread notifications"""
        try:
            async def get_unread_count(client):
                count = await client.get("user_notifications:unread_count")
                return int(count) if count else 0
            
            return await self.execute_with_retry(get_unread_count)
        except Exception as e:
            logger.error(f"Failed to get unread notifications count: {e}")
            return 0
    
    async def mark_notification_read(self, notification_id: str) -> bool:
        """Mark a notification as read"""
        try:
            async def mark_read(client):
                # Get all notifications and find the one to mark as read
                notifications = await client.zrange("user_notifications", 0, -1, withscores=True)
                
                for notification_json, score in notifications:
                    try:
                        notification_data = json.loads(notification_json)
                        if notification_data.get('id') == notification_id:
                            # Update status to read
                            notification_data['status'] = 'read'
                            
                            # Update in sorted set
                            pipe = client.pipeline()
                            pipe.zrem("user_notifications", notification_json)
                            pipe.zadd("user_notifications", {json.dumps(notification_data): score})
                            
                            # Decrease unread count if it was unread
                            if notification_data.get('status') != 'read':
                                pipe.decr("user_notifications:unread_count")
                            
                            await pipe.execute()
                            return True
                    except json.JSONDecodeError:
                        continue
                
                return False
            
            return await self.execute_with_retry(mark_read)
        except Exception as e:
            logger.error(f"Failed to mark notification {notification_id} as read: {e}")
            return False
    
    async def mark_all_notifications_read(self) -> int:
        """Mark all notifications as read"""
        try:
            async def mark_all_read(client):
                # Get all notifications
                notifications = await client.zrange("user_notifications", 0, -1, withscores=True)
                marked_count = 0
                
                pipe = client.pipeline()
                
                for notification_json, score in notifications:
                    try:
                        notification_data = json.loads(notification_json)
                        if notification_data.get('status') != 'read':
                            # Update status to read
                            notification_data['status'] = 'read'
                            
                            # Remove old and add updated
                            pipe.zrem("user_notifications", notification_json)
                            pipe.zadd("user_notifications", {json.dumps(notification_data): score})
                            marked_count += 1
                    except json.JSONDecodeError:
                        continue
                
                # Reset unread count
                pipe.set("user_notifications:unread_count", 0)
                
                await pipe.execute()
                return marked_count
            
            return await self.execute_with_retry(mark_all_read)
        except Exception as e:
            logger.error(f"Failed to mark all notifications as read: {e}")
            return 0
    
    async def delete_notification(self, notification_id: str) -> bool:
        """Delete a notification"""
        try:
            async def delete_notification_data(client):
                # Get all notifications and find the one to delete
                notifications = await client.zrange("user_notifications", 0, -1)
                
                for notification_json in notifications:
                    try:
                        notification_data = json.loads(notification_json)
                        if notification_data.get('id') == notification_id:
                            # Remove from sorted set
                            removed = await client.zrem("user_notifications", notification_json)
                            
                            # Decrease unread count if it was unread
                            if notification_data.get('status') != 'read':
                                await client.decr("user_notifications:unread_count")
                            
                            return removed > 0
                    except json.JSONDecodeError:
                        continue
                
                return False
            
            return await self.execute_with_retry(delete_notification_data)
        except Exception as e:
            logger.error(f"Failed to delete notification {notification_id}: {e}")
            return False
    
    async def monitor_new_notifications(self, last_timestamp: float) -> List[Dict[str, Any]]:
        """Get notifications created after a given timestamp"""
        try:
            async def get_new_notifications(client):
                # Get notifications with score (timestamp) greater than last_timestamp
                notifications = await client.zrangebyscore(
                    "user_notifications", 
                    last_timestamp, 
                    "+inf", 
                    withscores=True
                )
                
                parsed_notifications = []
                for notification_json, score in notifications:
                    try:
                        notification_data = json.loads(notification_json)
                        notification_data['timestamp'] = datetime.fromtimestamp(score).isoformat()
                        
                        try:
                            notification_obj = NotificationData.from_dict(notification_data)
                            parsed_notifications.append(notification_obj.to_dict())
                        except Exception:
                            parsed_notifications.append(notification_data)
                    except json.JSONDecodeError:
                        continue
                
                return parsed_notifications
            
            return await self.execute_with_retry(get_new_notifications)
        except Exception as e:
            logger.error(f"Failed to monitor new notifications: {e}")
            return []
    
    async def cleanup_old_notifications(self, retention_hours: int = 24) -> int:
        """Clean up old notifications"""
        try:
            async def cleanup_notifications(client):
                cutoff = datetime.now() - timedelta(hours=retention_hours)
                cutoff_timestamp = cutoff.timestamp()
                
                # Remove old notifications
                removed = await client.zremrangebyscore("user_notifications", 0, cutoff_timestamp)
                
                return removed
            
            return await self.execute_with_retry(cleanup_notifications)
        except Exception as e:
            logger.error(f"Failed to cleanup old notifications: {e}")
            return 0