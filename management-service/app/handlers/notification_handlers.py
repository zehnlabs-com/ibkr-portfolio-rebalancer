"""
Notification handlers for the management service
"""
import json
import logging
from datetime import datetime
from typing import List, Optional
import redis.asyncio as redis
from app.models.notification_models import (
    Notification, NotificationsResponse, UnreadCountResponse,
    MarkReadResponse, MarkAllReadResponse, DeleteNotificationResponse
)

logger = logging.getLogger(__name__)


class NotificationHandlers:
    """Handlers for notification-related operations"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def get_notifications(self, offset: int = 0, limit: int = 50) -> NotificationsResponse:
        """Get paginated notifications ordered by timestamp (newest first)"""
        try:
            # Get total count
            total = await self.redis.zcard('user_notifications')
            
            # Get notifications in descending order (newest first)
            notification_data = await self.redis.zrevrange(
                'user_notifications', 
                offset, 
                offset + limit - 1
            )
            
            notifications = []
            for notification_json in notification_data:
                try:
                    data = json.loads(notification_json)
                    notification = Notification(
                        id=data['id'],
                        account_id=data['account_id'],
                        strategy_name=data['strategy_name'],
                        event_type=data['event_type'],
                        message=data['message'],
                        timestamp=datetime.fromisoformat(data['timestamp']),
                        status=data['status'],
                        markdown_body=data['markdown_body']
                    )
                    notifications.append(notification)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse notification: {e}")
                    continue

            has_more = offset + limit < total
            
            return NotificationsResponse(
                notifications=notifications,
                total=total,
                has_more=has_more
            )

        except Exception as e:
            logger.error(f"Failed to get notifications: {e}")
            return NotificationsResponse(notifications=[], total=0, has_more=False)

    async def get_unread_count(self) -> UnreadCountResponse:
        """Get count of unread notifications"""
        try:
            count = await self.redis.get('user_notifications:unread_count')
            unread_count = int(count) if count is not None else 0
            return UnreadCountResponse(count=unread_count)
        except Exception as e:
            logger.error(f"Failed to get unread count: {e}")
            return UnreadCountResponse(count=0)

    async def mark_notification_read(self, notification_id: str) -> MarkReadResponse:
        """Mark a specific notification as read"""
        try:
            # Get all notifications to find the one with matching ID
            all_notifications = await self.redis.zrange('user_notifications', 0, -1)
            
            for notification_json in all_notifications:
                try:
                    data = json.loads(notification_json)
                    if data['id'] == notification_id:
                        # Update status to read if it was new
                        if data['status'] == 'new':
                            data['status'] = 'read'
                            updated_json = json.dumps(data)
                            
                            # Get the score (timestamp) for this notification
                            score = await self.redis.zscore('user_notifications', notification_json)
                            
                            # Remove old entry and add updated one
                            pipe = self.redis.pipeline()
                            pipe.zrem('user_notifications', notification_json)
                            pipe.zadd('user_notifications', {updated_json: score})
                            pipe.decr('user_notifications:unread_count')
                            await pipe.execute()
                            
                            return MarkReadResponse(
                                success=True,
                                message="Notification marked as read"
                            )
                        else:
                            return MarkReadResponse(
                                success=True,
                                message="Notification was already read"
                            )
                except (json.JSONDecodeError, KeyError):
                    continue
            
            return MarkReadResponse(
                success=False,
                message="Notification not found"
            )
            
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {e}")
            return MarkReadResponse(
                success=False,
                message=f"Error marking notification as read: {str(e)}"
            )

    async def mark_all_read(self) -> MarkAllReadResponse:
        """Mark all notifications as read"""
        try:
            all_notifications = await self.redis.zrange('user_notifications', 0, -1)
            marked_count = 0
            
            pipe = self.redis.pipeline()
            
            for notification_json in all_notifications:
                try:
                    data = json.loads(notification_json)
                    if data['status'] == 'new':
                        data['status'] = 'read'
                        updated_json = json.dumps(data)
                        
                        # Get the score (timestamp) for this notification
                        score = await self.redis.zscore('user_notifications', notification_json)
                        
                        # Remove old entry and add updated one
                        pipe.zrem('user_notifications', notification_json)
                        pipe.zadd('user_notifications', {updated_json: score})
                        marked_count += 1
                except (json.JSONDecodeError, KeyError):
                    continue
            
            # Reset unread count to 0
            pipe.set('user_notifications:unread_count', 0)
            await pipe.execute()
            
            return MarkAllReadResponse(
                success=True,
                marked_count=marked_count,
                message=f"Marked {marked_count} notifications as read"
            )
            
        except Exception as e:
            logger.error(f"Failed to mark all notifications as read: {e}")
            return MarkAllReadResponse(
                success=False,
                marked_count=0,
                message=f"Error marking all notifications as read: {str(e)}"
            )

    async def delete_notification(self, notification_id: str) -> DeleteNotificationResponse:
        """Delete a specific notification"""
        try:
            # Get all notifications to find the one with matching ID
            all_notifications = await self.redis.zrange('user_notifications', 0, -1)
            
            for notification_json in all_notifications:
                try:
                    data = json.loads(notification_json)
                    if data['id'] == notification_id:
                        # Remove the notification
                        pipe = self.redis.pipeline()
                        pipe.zrem('user_notifications', notification_json)
                        
                        # If it was unread, decrement the unread count
                        if data['status'] == 'new':
                            pipe.decr('user_notifications:unread_count')
                        
                        await pipe.execute()
                        
                        return DeleteNotificationResponse(
                            success=True,
                            message="Notification deleted successfully"
                        )
                except (json.JSONDecodeError, KeyError):
                    continue
            
            return DeleteNotificationResponse(
                success=False,
                message="Notification not found"
            )
            
        except Exception as e:
            logger.error(f"Failed to delete notification: {e}")
            return DeleteNotificationResponse(
                success=False,
                message=f"Error deleting notification: {str(e)}"
            )