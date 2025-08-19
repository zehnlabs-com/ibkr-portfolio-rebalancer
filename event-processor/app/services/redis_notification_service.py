"""
Redis Notification Service for Event Processor
Handles all notification operations in Redis
"""
import json
from typing import Dict, Any
from datetime import datetime, timedelta
from app.services.base_redis_service import BaseRedisService
from app.models.notification_data import NotificationData
from app.config import config
from app.logger import AppLogger

app_logger = AppLogger(__name__)


class RedisNotificationService(BaseRedisService):
    """Service for notification operations in Redis"""
    
    def __init__(self):
        """Initialize Redis Notification Service"""
        redis_url = f"redis://{config.redis.host}:{config.redis.port}/{config.redis.db}"
        super().__init__(redis_url=redis_url)
    
    async def queue_notification(self, notification_data: NotificationData) -> None:
        """Queue a user notification using strongly typed NotificationData"""
        try:
            notification_dict = notification_data.to_dict()
            notification_dict['status'] = 'new'
            
            async def queue_operation(client):
                pipe = client.pipeline()
                pipe.zadd('user_notifications', {json.dumps(notification_dict): notification_data.created_at.timestamp()})
                pipe.incr('user_notifications:unread_count')
                return await pipe.execute()
            
            await self.execute_with_retry(queue_operation)
            
            app_logger.log_debug(f"Queued notification: {notification_data.event_type.value if notification_data.event_type else 'unknown'}")
            
        except Exception as e:
            app_logger.log_error(f"Failed to queue notification: {e}")
            raise
    
    async def cleanup_old_notifications(self, retention_hours: int = 24) -> int:
        """
        Clean up old notifications
        
        Returns:
            Number of notifications removed
        """
        try:
            cutoff = datetime.now() - timedelta(hours=retention_hours)
            cutoff_timestamp = cutoff.timestamp()
            
            async def cleanup_operation(client):
                # Get old notifications
                old_notifications = await client.zrangebyscore('user_notifications', 0, cutoff_timestamp)
                
                if not old_notifications:
                    return 0
                
                # Remove old notifications
                removed_count = 0
                for notification_json in old_notifications:
                    try:
                        notification = json.loads(notification_json)
                        if notification.get('status') == 'read':
                            await client.zrem('user_notifications', notification_json)
                            removed_count += 1
                        elif notification.get('status') == 'new':
                            # Keep unread notifications longer
                            await client.zrem('user_notifications', notification_json)
                            removed_count += 1
                    except Exception:
                        await client.zrem('user_notifications', notification_json)
                        removed_count += 1
                
                return removed_count
            
            removed = await self.execute_with_retry(cleanup_operation)
            
            if removed > 0:
                app_logger.log_info(f"Cleaned up {removed} old notifications")
            return removed
            
        except Exception as e:
            app_logger.log_error(f"Failed to cleanup notifications: {e}")
            return 0