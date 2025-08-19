"""
Notification Monitor Service for Real-time Notification Updates

This service monitors Redis for new notifications and broadcasts them to WebSocket clients.
"""
import json
import asyncio
import logging
from typing import Optional
from datetime import datetime
from app.services.redis_data_service import RedisDataService
from app.logger import setup_logger

logger = setup_logger(__name__)


class NotificationMonitorService:
    """Service for monitoring and broadcasting new notifications via WebSocket"""
    
    def __init__(self, redis_data_service: RedisDataService, websocket_manager):
        self.redis_data_service = redis_data_service
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
            
            # Get new notifications using Redis data service
            new_notifications = await self.redis_data_service.monitor_new_notifications(
                self._last_check_timestamp
            )
            
            if new_notifications:
                # Broadcast new notifications to WebSocket clients
                await self._broadcast_notifications(new_notifications)
                logger.debug(f"Broadcasted {len(new_notifications)} new notifications")
            
            # Update timestamp for next check
            self._last_check_timestamp = current_timestamp
            
        except Exception as e:
            logger.error(f"Failed to check for new notifications: {e}")
    
    async def _send_all_notifications(self) -> None:
        """Send all current notifications to newly connected clients"""
        try:
            # Get all notifications (limit to recent 100)
            all_notifications = await self.redis_data_service.get_notifications(100)
            
            if all_notifications:
                await self._broadcast_notifications(all_notifications, is_initial=True)
                logger.debug(f"Sent {len(all_notifications)} initial notifications")
                
        except Exception as e:
            logger.error(f"Failed to send initial notifications: {e}")
    
    async def _broadcast_notifications(self, notifications: list, is_initial: bool = False) -> None:
        """Broadcast notifications to all WebSocket clients"""
        try:
            if not notifications:
                return
                
            # Format message for WebSocket clients
            message = {
                "type": "notifications_initial" if is_initial else "notifications_update",
                "data": {
                    "notifications": notifications,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Broadcast to all connected WebSocket clients
            await self.websocket_manager.broadcast(message)
            
        except Exception as e:
            logger.error(f"Failed to broadcast notifications: {e}")