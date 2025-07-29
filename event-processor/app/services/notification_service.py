# -*- coding: utf-8 -*-
"""
User Notification Service for ntfy.sh integration with Redis-backed buffering
"""
import json
import asyncio  
import time
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
    Redis-backed user notification service with buffering for ntfy.sh
    Groups notifications by account and flushes periodically to prevent spam
    """
    
    def __init__(self):
        self.redis = None
        self._redis_url = f"redis://{config.redis.host}:{config.redis.port}/{config.redis.db}"
        self.flush_task = None
        self.running = False
        
        # Notification settings from config
        self.server_url = config.user_notification.server_url
        self.auth_token = config.user_notification.auth_token
        self.buffer_seconds = config.user_notification.buffer_seconds
        self.enabled = config.user_notification.enabled
        
        # Priority mapping
        self.priority_map = {
            'silent': 1,
            'default': 3, 
            'high': 4,
            'urgent': 5
        }
    
    async def _get_redis(self):
        """Get or create Redis connection"""
        if self.redis is None:
            self.redis = await redis.from_url(self._redis_url, decode_responses=True)
        return self.redis
    
    async def start(self):
        """Start the user notification service and background flush task"""
        if not self.enabled:
            app_logger.log_info("Notifications disabled, skipping start")
            return
            
        app_logger.log_info(f"Starting notification service with {self.buffer_seconds}s buffer")
        self.running = True
        self.flush_task = asyncio.create_task(self._flush_loop())
    
    async def stop(self):
        """Stop the user notification service"""
        if not self.running:
            return
            
        app_logger.log_info("Stopping notification service")
        self.running = False
        
        if self.flush_task and not self.flush_task.done():
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush before shutdown
        await self._flush_notifications()
    
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
        """Send immediate notification for connection error (not buffered)"""
        extra_details = {'error_message': error_message} if error_message else {}
        await self._send_immediate_notification(event, 'event_connection_error', extra_details)
    
    async def notify_event_critical_error(self, event: EventInfo, error_message: Optional[str] = None):
        """Send immediate notification for critical error (not buffered)"""
        extra_details = {'error_message': error_message} if error_message else {}
        await self._send_immediate_notification(event, 'event_critical_error', extra_details)
    
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
        Internal method to queue a notification for later batch sending
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
            
            # Create notification event
            timestamp = datetime.now()
            notification = UserNotificationEvent(
                event_type=event_type,
                message=self._format_event_message(event_type, details, timestamp),
                timestamp=timestamp,
                details=details
            )
            
            # Store in Redis buffer
            buffer_key = f"notifications:{event.account_id}"
            notification_data = {
                'event_type': notification.event_type,
                'message': notification.message,
                'timestamp': notification.timestamp.isoformat(),
                'details': notification.details
            }
            
            pipe = redis.pipeline()
            pipe.lpush(buffer_key, json.dumps(notification_data))
            pipe.sadd("pending_accounts", event.account_id)
            # Set expiry on buffer to prevent orphaned data
            pipe.expire(buffer_key, self.buffer_seconds * 2)
            await pipe.execute()
            
            app_logger.log_debug(f"Queued {event_type} notification for account {event.account_id}")
            
        except Exception as e:
            app_logger.log_error(f"Failed to queue notification: {e}")
    
    async def _send_immediate_notification(self, event: EventInfo, event_type: str, extra_details: Optional[Dict[str, Any]] = None):
        """
        Send immediate notification without buffering (for errors)
        """
        if not self.enabled:
            return
            
        try:
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
            
            # Create immediate notification
            timestamp = datetime.now()
            message = self._format_event_message(event_type, details, timestamp)
            title = f"{event.account_id} Portfolio Rebalancing"
            
            # Determine priority and emoji tags
            if 'error' in event_type:
                priority = 'urgent'
                emoji_tags = 'rotating_light'
            else:
                priority = 'default'
                emoji_tags = 'warning'
            
            # Send immediately to ntfy.sh
            await self._send_to_ntfy(event.account_id, title, message, priority, emoji_tags)
            
            app_logger.log_info(f"Sent immediate {event_type} notification for account {event.account_id}")
            
        except Exception as e:
            app_logger.log_error(f"Failed to send immediate notification: {e}")
    
    def _format_event_message(self, event_type: str, details: Dict[str, Any], timestamp: Optional[datetime] = None) -> str:
        """Format individual event message without markdown (mobile compatible)"""
        event_id = details.get('event_id', 'unknown')
        strategy_name = details.get('strategy_name', 'unknown')
        time_str = (timestamp or datetime.now()).strftime('%H:%M:%S')
        
        # Event type to message mapping without markdown (mobile compatible)
        event_formats = {
            'event_started': f"Rebalance started for strategy {strategy_name} at {time_str} with event Id {event_id}",
            'event_success_first': f"Rebalance completed for strategy {strategy_name} at {time_str} with event Id {event_id}",
            'event_success_retry': f"Rebalance completed after retry for strategy {strategy_name} at {time_str} with event Id {event_id}",
            'event_delayed': f"Rebalance delayed until {details.get('delayed_until', 'unknown')} for strategy {strategy_name} at {time_str} with event Id {event_id}",
            'event_retry': f"Rebalance queued for retry for strategy {strategy_name} at {time_str} with event Id {event_id}",
            'event_connection_error': f"Connection error for strategy {strategy_name} at {time_str} with event Id {event_id}{': ' + details.get('error_message', '') if details.get('error_message') else ''}",
            'event_critical_error': f"Critical error for strategy {strategy_name} at {time_str} with event Id {event_id}{': ' + details.get('error_message', '') if details.get('error_message') else ''}"
        }
        
        return event_formats.get(event_type, f"Event {event_type} for strategy {strategy_name} at {time_str} with event Id {event_id}")
    
    async def _flush_loop(self):
        """Background task to flush notifications periodically"""
        while self.running:
            try:
                await asyncio.sleep(self.buffer_seconds)
                if self.running:
                    await self._flush_notifications()
            except asyncio.CancelledError:
                break
            except Exception as e:
                app_logger.log_error(f"Error in notification flush loop: {e}")
                await asyncio.sleep(10)
    
    async def _flush_notifications(self):
        """Flush all buffered notifications by account"""
        if not self.enabled:
            return
            
        try:
            redis = await self._get_redis()
            
            # Get all accounts with pending notifications
            pending_accounts = await redis.smembers("pending_accounts")
            if not pending_accounts:
                app_logger.log_debug("No pending notifications to flush")
                return
            
            app_logger.log_debug(f"Flushing notifications for {len(pending_accounts)} accounts")
            
            # Process each account
            for account_id in pending_accounts:
                await self._flush_account_notifications(account_id)
            
            # Clear pending accounts set
            await redis.delete("pending_accounts")
            
        except Exception as e:
            app_logger.log_error(f"Failed to flush notifications: {e}")
    
    async def _flush_account_notifications(self, account_id: str):
        """Flush all notifications for a specific account"""
        try:
            redis = await self._get_redis()
            buffer_key = f"notifications:{account_id}"
            
            # Get all notifications for this account
            notifications_data = await redis.lrange(buffer_key, 0, -1)
            if not notifications_data:
                return
            
            # Parse notifications
            notifications = []
            for notification_json in reversed(notifications_data):  # Reverse to get chronological order
                try:
                    notification_data = json.loads(notification_json)
                    notifications.append(UserNotificationEvent(
                        event_type=notification_data['event_type'],
                        message=notification_data['message'],
                        timestamp=datetime.fromisoformat(notification_data['timestamp']),
                        details=notification_data['details']
                    ))
                except (json.JSONDecodeError, KeyError) as e:
                    app_logger.log_warning(f"Failed to parse notification data: {e}")
                    continue
            
            if notifications:
                # Group and send notification
                await self._send_grouped_notification(account_id, notifications)
                
                # Clear buffer for this account
                await redis.delete(buffer_key)
                
        except Exception as e:
            app_logger.log_error(f"Failed to flush notifications for account {account_id}: {e}")
    
    async def _send_grouped_notification(self, account_id: str, notifications: List[UserNotificationEvent]):
        """Send grouped notification for an account"""
        try:
            # Title with account ID
            title = f"{account_id} Portfolio Rebalancing"
            
            # Build message content with icons and Unicode line separators (mobile compatible)
            message_lines = []
            for i, notification in enumerate(notifications):
                if i > 0:
                    message_lines.append("━━━━━━━━━━")
                icon = self._get_event_icon(notification.event_type)
                message_lines.append(f"{icon} {notification.message}")
            
            message = "\n".join(message_lines)
            
            # Determine priority and emoji tags based on notification types
            priority, emoji_tags = self._determine_priority_and_tags(notifications)
            
            # Send to ntfy.sh
            await self._send_to_ntfy(account_id, title, message, priority, emoji_tags)
            
            app_logger.log_info(f"Sent grouped notification to account {account_id} with {len(notifications)} events")
            
        except Exception as e:
            app_logger.log_error(f"Failed to send grouped notification for account {account_id}: {e}")
    
    def _determine_priority_and_tags(self, notifications: List[UserNotificationEvent]) -> tuple[str, str]:
        """Determine priority and emoji tags for grouped notifications"""
        has_error = any('error' in notification.event_type for notification in notifications)
        has_warning = any(notification.event_type in ['event_delayed', 'event_retry', 'event_success_retry'] 
                         for notification in notifications)
        has_success = any(notification.event_type in ['event_success_first', 'event_success_retry'] 
                         for notification in notifications)
        
        # Use 'file_folder' emoji for grouped notifications to indicate multiple items
        if has_error:
            return 'urgent', 'file_folder'
        elif has_warning:
            return 'default', 'file_folder'
        elif has_success:
            return 'default', 'file_folder'
        else:
            return 'default', 'file_folder'
    
    def _get_event_icon(self, event_type: str) -> str:
        """Get appropriate icon for individual event types"""
        event_icons = {
            'event_started': '▶',
            'event_success_first': '✅',
            'event_success_retry': '🔄',
            'event_delayed': '⏰',
            'event_retry': '🔄',
            'event_connection_error': '🌐',
            'event_critical_error': '🚨'
        }
        return event_icons.get(event_type, '📈')
    
    async def _send_to_ntfy(self, account_id: str, title: str, message: str, priority: str = 'default', tags: str = 'chart_with_upwards_trend'):
        """Send notification to ntfy.sh"""
        try:
            channel = f"ZLF-2025-{account_id}"
            url = f"{self.server_url}/{channel}"
            
            headers = {
                'Title': title,
                'Priority': str(self.priority_map.get(priority, 3)),
                'Tags': tags,
                'Content-Type': 'text/plain'
            }
            
            # Add auth token if configured
            if self.auth_token:
                headers['Authorization'] = f"Bearer {self.auth_token}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=message, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        app_logger.log_info(f"Successfully sent notification to {channel}")
                    else:
                        app_logger.log_warning(f"ntfy.sh returned status {response.status} for {channel}: {await response.text()}")
                        
        except asyncio.TimeoutError:
            app_logger.log_warning(f"Timeout sending notification to {account_id}")
        except Exception as e:
            app_logger.log_error(f"Failed to send notification to ntfy.sh: {e}")
    
    async def is_connected(self) -> bool:
        """Check if service is connected and operational"""
        try:
            redis = await self._get_redis()
            await redis.ping()
            return True
        except Exception:
            return False