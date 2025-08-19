"""
Notification cleanup service for removing old read notifications
"""
import json
import logging
import asyncio
from datetime import datetime, timedelta
from app.services.redis_data_service import RedisDataService

logger = logging.getLogger(__name__)


class NotificationCleanupService:
    """Service for cleaning up old read notifications"""

    def __init__(self, redis_data_service: RedisDataService):
        self.redis_data_service = redis_data_service
        self.cleanup_task = None
        self.running = False

    async def start(self):
        """Start the cleanup background task"""
        logger.info("Starting notification cleanup service")
        self.running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        """Stop the cleanup background task"""
        if not self.running:
            return

        logger.info("Stopping notification cleanup service")
        self.running = False

        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self):
        """Background task to cleanup read notifications older than 7 days"""
        while self.running:
            try:
                # Run cleanup every 24 hours
                await asyncio.sleep(86400)
                if self.running:
                    await self._cleanup_old_notifications()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in notification cleanup loop: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour on error

    async def _cleanup_old_notifications(self):
        """Remove read notifications older than 7 days"""
        try:
            # Use RedisDataService to cleanup old notifications (7 days retention)
            removed_count = await self.redis_data_service.cleanup_old_notifications(7 * 24)  # 7 days in hours
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old read notifications")

        except Exception as e:
            logger.error(f"Failed to cleanup old notifications: {e}")