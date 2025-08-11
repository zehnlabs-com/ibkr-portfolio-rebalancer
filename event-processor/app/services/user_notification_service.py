# -*- coding: utf-8 -*-
"""
User Notification Service with Redis-based notification queue
"""
import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import redis.asyncio as redis
import aiohttp
from dataclasses import dataclass
from app.config import config
from app.logger import AppLogger
from app.models.events import EventInfo

app_logger = AppLogger(__name__)


@dataclass
class UserNotificationEvent:
    """Individual notification event"""
    event_type: str
    message: str
    timestamp: datetime
    details: Dict[str, Any]


class UserNotificationService:
    """
    Redis-based user notification service
    Stores notifications in a global queue with automatic cleanup
    """
    
    def __init__(self):
        self.redis = None
        self._redis_url = f"redis://{config.redis.host}:{config.redis.port}/{config.redis.db}"
        self.cleanup_task = None
        self.running = False
        
        # Notification settings from config
        self.enabled = config.user_notification.enabled
        self.management_api_url = "http://management-service:8000"
    
    async def _get_redis(self):
        """Get or create Redis connection"""
        if self.redis is None:
            self.redis = await redis.from_url(self._redis_url, decode_responses=True)
        return self.redis
    
    async def start(self):
        """Start the user notification service and background cleanup task"""
        if not self.enabled:
            app_logger.log_info("Notifications disabled, skipping start")
            return
            
        app_logger.log_info("Starting notification service")
        self.running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        """Stop the user notification service"""
        if not self.running:
            return
            
        app_logger.log_info("Stopping notification service")
        self.running = False
        
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def notify_event_started(self, event: EventInfo):
        """Queue notification for event start"""
        await self._queue_notification_internal(event, 'event_started')
    
    async def notify_event_completed(self, event: EventInfo):
        """Queue notification for successful event completion on first try"""
        await self._queue_notification_internal(event, 'event_success_first')
    
    async def notify_event_completed_with_retry(self, event: EventInfo):
        """Queue notification for successful event completion after retry"""
        await self._queue_notification_internal(event, 'event_success_retry')
    
    async def notify_event_execution_delayed(self, event: EventInfo, delayed_until: str):
        """Queue notification for delayed event with specific delay time"""
        extra_details = {'delayed_until': delayed_until}
        await self._queue_notification_internal(event, 'event_delayed', extra_details)
    
    async def notify_event_will_retry(self, event: EventInfo):
        """Queue notification for event being queued for retry"""
        await self._queue_notification_internal(event, 'event_retry')
    
    async def notify_event_connection_error(self, event: EventInfo, error_message: Optional[str] = None):
        """Queue notification for connection error"""
        extra_details = {'error_message': error_message} if error_message else {}
        await self._queue_notification_internal(event, 'event_connection_error', extra_details)
    
    async def notify_event_critical_error(self, event: EventInfo, error_message: Optional[str] = None):
        """Queue notification for critical error"""
        extra_details = {'error_message': error_message} if error_message else {}
        await self._queue_notification_internal(event, 'event_critical_error', extra_details)
    
    async def send_notification(self, event_info: EventInfo, event_type: str, extra_details: Optional[Dict[str, Any]] = None):
        """Route notification to appropriate method based on event type"""
        try:
            if event_type == 'event_started':
                await self.notify_event_started(event_info)
            elif event_type == 'event_success_first':
                await self.notify_event_completed(event_info)
            elif event_type == 'event_success_retry':
                await self.notify_event_completed_with_retry(event_info)
            elif event_type == 'event_delayed':
                delayed_until = event_info.payload.get('delayed_until', 'unknown')
                await self.notify_event_execution_delayed(event_info, delayed_until)
            elif event_type == 'event_retry':
                await self.notify_event_will_retry(event_info)  
            elif event_type == 'event_connection_error':
                error_message = extra_details.get('error_message') if extra_details else None
                await self.notify_event_connection_error(event_info, error_message)
            elif event_type == 'event_critical_error':
                error_message = extra_details.get('error_message') if extra_details else None
                await self.notify_event_critical_error(event_info, error_message)
            else:
                app_logger.log_warning(f"Unknown event type for notification: {event_type}")
            
        except Exception as e:
            app_logger.log_warning(f"Failed to send notification: {e}")
    
    async def _queue_notification_internal(self, event: EventInfo, event_type: str, extra_details: Optional[Dict[str, Any]] = None):
        """
        Internal method to queue a notification in the global notification queue
        """
        if not self.enabled:
            return
            
        try:
            redis = await self._get_redis()
            
            # Extract strategy name from event payload
            strategy_name = event.payload.get('strategy_name', 'unknown')
            
            # Build details from event information
            details = {
                'event_id': event.event_id,
                'account_id': event.account_id,
                'strategy_name': strategy_name,
                'exec_command': event.exec_command,
                'times_queued': event.times_queued
            }
            
            # Add extra details if provided
            if extra_details:
                details.update(extra_details)
            
            # Create notification
            timestamp = datetime.now()
            notification_id = str(uuid.uuid4())
            
            notification_data = {
                'id': notification_id,
                'account_id': event.account_id,
                'strategy_name': strategy_name,
                'event_type': event_type,
                'message': self._format_event_message(event_type, details, timestamp),
                'timestamp': timestamp.isoformat(),
                'status': 'new',
                'markdown_body': self._format_markdown_body(event_type, details, timestamp)
            }
            
            # Store in Redis ZSET ordered by timestamp
            pipe = redis.pipeline()
            pipe.zadd('user_notifications', {json.dumps(notification_data): timestamp.timestamp()})
            pipe.incr('user_notifications:unread_count')
            await pipe.execute()
            
            app_logger.log_debug(f"Queued {event_type} notification for account {event.account_id}")
            
        except Exception as e:
            app_logger.log_error(f"Failed to queue notification: {e}")
    
    
    def _format_event_message(self, event_type: str, details: Dict[str, Any], timestamp: Optional[datetime] = None) -> str:
        """Format concise event message for notification title"""
        strategy_name = details.get('strategy_name', 'unknown')
        time_str = (timestamp or datetime.now()).strftime('%H:%M:%S')
        
        event_formats = {
            'event_started': f"Rebalance started for {strategy_name} at {time_str}",
            'event_success_first': f"Rebalance completed for {strategy_name} at {time_str}",
            'event_success_retry': f"Rebalance completed after retry for {strategy_name} at {time_str}",
            'event_delayed': f"Rebalance delayed until {details.get('delayed_until', 'unknown')} for {strategy_name} at {time_str}",
            'event_retry': f"Rebalance queued for retry for {strategy_name} at {time_str}",
            'event_connection_error': f"Connection error for {strategy_name} at {time_str}",
            'event_critical_error': f"Critical error for {strategy_name} at {time_str}"
        }
        
        return event_formats.get(event_type, f"Event {event_type} for {strategy_name} at {time_str}")
    
    def _format_markdown_body(self, event_type: str, details: Dict[str, Any], timestamp: Optional[datetime] = None) -> str:
        """Format detailed markdown body for notification"""
        event_id = details.get('event_id', 'unknown')
        strategy_name = details.get('strategy_name', 'unknown')
        account_id = details.get('account_id', 'unknown')
        exec_command = details.get('exec_command', 'unknown')
        times_queued = details.get('times_queued', 0)
        time_str = (timestamp or datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
        
        base_info = f"""**Event Details**
- Event ID: `{event_id}`
- Account: `{account_id}`
- Strategy: `{strategy_name}`
- Command: `{exec_command}`
- Times Queued: `{times_queued}`
- Timestamp: `{time_str}`"""
        
        if event_type in ['event_connection_error', 'event_critical_error'] and details.get('error_message'):
            base_info += f"\n\n**Error Message**\n```\n{details['error_message']}\n```"
        
        if event_type == 'event_delayed' and details.get('delayed_until'):
            base_info += f"\n\n**Delayed Until**: {details['delayed_until']}"
        
        return base_info
    
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
                app_logger.log_error(f"Error in notification cleanup loop: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour on error
    
    async def _cleanup_old_notifications(self):
        """Remove read notifications older than 7 days"""
        try:
            redis = await self._get_redis()
            
            # Calculate cutoff timestamp (7 days ago)
            cutoff_time = datetime.now() - timedelta(days=7)
            cutoff_timestamp = cutoff_time.timestamp()
            
            # Get notifications older than cutoff
            old_notifications = await redis.zrangebyscore('user_notifications', 0, cutoff_timestamp)
            
            removed_count = 0
            for notification_json in old_notifications:
                try:
                    notification_data = json.loads(notification_json)
                    if notification_data.get('status') == 'read':
                        # Remove read notification
                        await redis.zrem('user_notifications', notification_json)
                        removed_count += 1
                except (json.JSONDecodeError, KeyError):
                    # Remove corrupted data
                    await redis.zrem('user_notifications', notification_json)
                    removed_count += 1
            
            if removed_count > 0:
                app_logger.log_info(f"Cleaned up {removed_count} old read notifications")
            
        except Exception as e:
            app_logger.log_error(f"Failed to cleanup old notifications: {e}")
    
    async def _broadcast_count_update(self, unread_count: int):
        """Broadcast unread count update to WebSocket clients via management API"""
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{self.management_api_url}/api/internal/broadcast-notification-count",
                    json={"unread_count": unread_count},
                    timeout=aiohttp.ClientTimeout(total=5)
                )
        except Exception as e:
            app_logger.log_debug(f"Failed to broadcast count update: {e}")
    
    async def is_connected(self) -> bool:
        """Check if service is connected and operational"""
        try:
            redis = await self._get_redis()
            await redis.ping()
            return True
        except Exception:
            return False