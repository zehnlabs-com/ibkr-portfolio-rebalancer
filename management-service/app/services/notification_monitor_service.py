"""
Notification Monitor Service for Real-time Notification Updates

This service monitors Redis for new notifications and broadcasts them to WebSocket clients.
"""
import json
import asyncio
import logging
from typing import Optional
from datetime import datetime
import redis.asyncio as redis

from app.logger import setup_logger

logger = setup_logger(__name__)


class NotificationMonitorService:
    """Service for monitoring and broadcasting new notifications via WebSocket"""
    
    def __init__(self, redis_url: str, websocket_manager):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.websocket_manager = websocket_manager
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        self._last_check_timestamp = None
        
    async def start(self) -> None:
        """Start the notification monitor"""
        if self._running:
            logger.warning("Notification monitor service already running")
            return
            
        try:
            # Create Redis connection
            self.redis = await redis.from_url(self.redis_url, decode_responses=True)
            
            # Test Redis connection
            await self.redis.ping()
            
            self._running = True
            self._last_check_timestamp = datetime.now().timestamp()
            
            # Start the monitor task
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            
            # Send initial notifications on startup
            await self._send_all_notifications()
            
            logger.info("Notification monitor service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start notification monitor service: {e}")
            await self.stop()
            raise
            
    async def stop(self) -> None:
        """Stop the notification monitor"""
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        if self.redis:
            await self.redis.close()
            self.redis = None
                
        logger.info("Notification monitor service stopped")
        
    async def _monitor_loop(self) -> None:
        """Main monitor loop that checks for new notifications"""
        while self._running:
            try:
                # Check for new notifications every 2 seconds
                await asyncio.sleep(2)
                
                if self._running:
                    await self._check_for_new_notifications()
                    
            except Exception as e:
                logger.error(f"Error in notification monitor loop: {e}")
                await asyncio.sleep(5)
                
    async def _check_for_new_notifications(self) -> None:
        """Check for notifications added since last check"""
        try:
            current_timestamp = datetime.now().timestamp()
            
            # Get notifications added since last check
            new_notifications = await self.redis.zrangebyscore(
                'user_notifications',
                self._last_check_timestamp,
                current_timestamp
            )
            
            if new_notifications:
                logger.info(f"Found {len(new_notifications)} new notifications")
                
                # Parse and broadcast each new notification
                for notification_json in new_notifications:
                    try:
                        notification_data = json.loads(notification_json)
                        await self._broadcast_notification(notification_data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse notification: {e}")
                
                # Also broadcast updated unread count
                await self._broadcast_unread_count()
            
            self._last_check_timestamp = current_timestamp
            
        except Exception as e:
            logger.error(f"Failed to check for new notifications: {e}")
            
    async def _send_all_notifications(self) -> None:
        """Send all existing notifications on initial connection"""
        try:
            # Get all notifications (newest first)
            all_notifications = await self.redis.zrevrange('user_notifications', 0, -1)
            
            notifications_list = []
            for notification_json in all_notifications:
                try:
                    notification_data = json.loads(notification_json)
                    notifications_list.append(notification_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse notification: {e}")
                    continue
            
            if notifications_list:
                # Send all notifications as a batch
                message = {
                    "type": "notifications",
                    "action": "initial",
                    "data": notifications_list
                }
                await self.websocket_manager.broadcast(message)
                logger.info(f"Sent {len(notifications_list)} initial notifications")
            
            # Also send unread count
            await self._broadcast_unread_count()
            
        except Exception as e:
            logger.error(f"Failed to send initial notifications: {e}")
            
    async def _broadcast_notification(self, notification_data: dict) -> None:
        """Broadcast a single notification to all WebSocket clients"""
        try:
            message = {
                "type": "notification",
                "action": "new",
                "data": notification_data
            }
            await self.websocket_manager.broadcast(message)
            logger.info(f"Broadcast new notification: {notification_data.get('id')}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast notification: {e}")
            
    async def _broadcast_unread_count(self) -> None:
        """Broadcast updated unread count to all WebSocket clients"""
        try:
            count = await self.redis.get('user_notifications:unread_count')
            unread_count = int(count) if count is not None else 0
            
            message = {
                "type": "notification_count",
                "data": {"unread_count": unread_count}
            }
            await self.websocket_manager.broadcast(message)
            logger.info(f"Broadcast unread count: {unread_count}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast unread count: {e}")
    
    async def handle_notification_update(self, notification_id: str, action: str) -> None:
        """Handle notification updates (mark read, delete) and broadcast changes"""
        try:
            if action == "read" or action == "delete":
                # Broadcast updated unread count
                await self._broadcast_unread_count()
                
                # Broadcast the action so frontend can update
                message = {
                    "type": "notification_update",
                    "action": action,
                    "data": {"notification_id": notification_id}
                }
                await self.websocket_manager.broadcast(message)
                
            elif action == "mark_all_read":
                # Broadcast mark all read action
                message = {
                    "type": "notification_update",
                    "action": "mark_all_read",
                    "data": {}
                }
                await self.websocket_manager.broadcast(message)
                
                # Broadcast updated unread count
                await self._broadcast_unread_count()
                
        except Exception as e:
            logger.error(f"Failed to handle notification update: {e}")