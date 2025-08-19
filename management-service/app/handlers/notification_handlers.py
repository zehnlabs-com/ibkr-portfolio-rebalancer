"""
Notification handlers for the management service
"""
import logging
from datetime import datetime
from typing import List, Optional
from app.services.redis_data_service import RedisDataService
from app.models.notification_models import (
    Notification, NotificationsResponse, UnreadCountResponse,
    MarkReadResponse, MarkAllReadResponse, DeleteNotificationResponse
)

logger = logging.getLogger(__name__)


class NotificationHandlers:
    """Handlers for notification-related operations"""

    def __init__(self, redis_data_service: RedisDataService):
        self.redis_data_service = redis_data_service

    async def get_notifications(self, offset: int = 0, limit: int = 50) -> NotificationsResponse:
        """Get paginated notifications ordered by timestamp (newest first)"""
        try:
            # Get total count and notifications
            total = await self.redis_data_service.get_notifications_count()
            notifications_data = await self.redis_data_service.get_notifications(limit + offset)
            
            # Apply offset and limit manually since Redis data service returns all
            paginated_data = notifications_data[offset:offset + limit]
            
            notifications = []
            for data in paginated_data:
                try:
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
                except KeyError as e:
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
            count = await self.redis_data_service.get_unread_notifications_count()
            return UnreadCountResponse(count=count)
        except Exception as e:
            logger.error(f"Failed to get unread count: {e}")
            return UnreadCountResponse(count=0)

    async def mark_notification_read(self, notification_id: str) -> MarkReadResponse:
        """Mark a specific notification as read"""
        try:
            success = await self.redis_data_service.mark_notification_read(notification_id)
            
            if success:
                return MarkReadResponse(
                    success=True,
                    message="Notification marked as read"
                )
            else:
                return MarkReadResponse(
                    success=False,
                    message="Notification not found or already read"
                )
                
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {e}")
            return MarkReadResponse(
                success=False,
                message=f"Failed to mark notification as read: {str(e)}"
            )

    async def mark_all_notifications_read(self) -> MarkAllReadResponse:
        """Mark all notifications as read"""
        try:
            marked_count = await self.redis_data_service.mark_all_notifications_read()
            
            return MarkAllReadResponse(
                success=True,
                message=f"Marked {marked_count} notifications as read",
                marked_count=marked_count
            )
            
        except Exception as e:
            logger.error(f"Failed to mark all notifications as read: {e}")
            return MarkAllReadResponse(
                success=False,
                message=f"Failed to mark all notifications as read: {str(e)}",
                marked_count=0
            )

    async def delete_notification(self, notification_id: str) -> DeleteNotificationResponse:
        """Delete a specific notification"""
        try:
            success = await self.redis_data_service.delete_notification(notification_id)
            
            if success:
                return DeleteNotificationResponse(
                    success=True,
                    message="Notification deleted"
                )
            else:
                return DeleteNotificationResponse(
                    success=False,
                    message="Notification not found"
                )
                
        except Exception as e:
            logger.error(f"Failed to delete notification: {e}")
            return DeleteNotificationResponse(
                success=False,
                message=f"Failed to delete notification: {str(e)}"
            )