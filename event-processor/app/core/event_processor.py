"""
Refactored event processor using command pattern.
"""

import asyncio
from typing import Dict, Any
from app.core.service_container import ServiceContainer
from app.commands.base import CommandStatus
from app.models.events import EventInfo
from app.config import config
from app.logger import AppLogger

app_logger = AppLogger(__name__)


class EventProcessor:
    """Main event processing class using command pattern"""
    
    def __init__(self, service_container: ServiceContainer):
        self.service_container = service_container
        self.running = False
        self.retry_processor_task = None
        self.delayed_processor_task = None
        self.processing_tasks = set()
        self.semaphore = None
    
    async def start_processing(self):
        """Start the event processing loop"""
        app_logger.log_info("Starting event processing loop...")
        
        try:
            self.running = True
            
            # Initialize semaphore for concurrent processing
            max_concurrent = config.processing.max_concurrent_events
            self.semaphore = asyncio.Semaphore(max_concurrent)
            app_logger.log_info(f"Event processing loop started with max {max_concurrent} concurrent events")
            
            # Start retry event processor task
            self.retry_processor_task = asyncio.create_task(self._retry_event_processor())
            
            # Start delayed event processor task
            self.delayed_processor_task = asyncio.create_task(self._delayed_event_processor())
            
            # Start main processing loop
            await self._main_loop()
            
        except Exception as e:
            app_logger.log_error(f"Failed to start event processing loop: {e}")
            raise
    
    async def stop_processing(self):
        """Stop the event processing loop"""
        if not self.running:
            return
            
        app_logger.log_info("Stopping event processing loop...")
        self.running = False
        
        # Cancel all active processing tasks
        for task in list(self.processing_tasks):
            if not task.done():
                task.cancel()
        
        # Wait for all processing tasks to complete
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks, return_exceptions=True)
        
        # Cancel retry processor task
        if self.retry_processor_task and not self.retry_processor_task.done():
            self.retry_processor_task.cancel()
            try:
                await self.retry_processor_task
            except asyncio.CancelledError:
                pass
        
        # Cancel delayed processor task
        if self.delayed_processor_task and not self.delayed_processor_task.done():
            self.delayed_processor_task.cancel()
            try:
                await self.delayed_processor_task
            except asyncio.CancelledError:
                pass
        
        app_logger.log_info("Event processing loop stopped")
    
    async def _main_loop(self):
        """Main event processing loop with concurrent processing"""
        app_logger.log_info("Starting main processing loop")
        
        queue_service = self.service_container.get_queue_service()
        
        while self.running:
            try:
                # Clean up completed tasks
                completed_tasks = {task for task in self.processing_tasks if task.done()}
                self.processing_tasks -= completed_tasks
                
                # Check if we can start more tasks
                if len(self.processing_tasks) < config.processing.max_concurrent_events:
                    app_logger.log_debug("Checking for events in queue...")
                    # Get event from queue with timeout
                    event_info = await queue_service.get_next_event()
                    
                    if event_info:
                        app_logger.log_debug(f"Starting concurrent processing for event: {event_info.event_id}", event_info)
                        # Create task for concurrent processing
                        task = asyncio.create_task(self._process_event_with_semaphore(event_info))
                        self.processing_tasks.add(task)
                    else:
                        app_logger.log_debug("No events available, waiting...")
                        await asyncio.sleep(5)
                else:
                    # At max capacity, wait a bit before checking again
                    await asyncio.sleep(1)
                    
            except Exception as e:
                app_logger.log_error(f"Error in main loop: {e}")
                await asyncio.sleep(10)
    
    async def process_event(self, event_info: EventInfo):
        """Process a single event using command pattern"""
        app_logger.log_debug("Processing event", event_info)
        
        queue_service = self.service_container.get_queue_service()
        notification_service = self.service_container.get_notification_service()
        
        try:
            # Send event started notification
            await self._send_event_notification(notification_service, event_info, 'event_started')
            
            # Times queued tracking now handled in Redis only
            
            # Get command factory and create command
            command_factory = self.service_container.get_command_factory()
            command = command_factory.create_command(event_info.exec_command, event_info.event_id, event_info.account_id, event_info)
            
            if not command:
                await self._handle_permanent_failure(event_info, f"No command handler found for: {event_info.exec_command}")
                return
            
            # Execute command with services
            services = self.service_container.get_services()
            result = await command.execute(services)
            
            # Handle command result
            if result.status == CommandStatus.SUCCESS:
                app_logger.log_info(f"Command executed successfully: {result.message}", event_info)
                
                # Send success notification (different types for first vs retry)
                success_event_type = 'event_success_first' if event_info.times_queued <= 1 else 'event_success_retry'
                await self._send_event_notification(notification_service, event_info, success_event_type)
                
                # Remove from active events set after successful processing
                await queue_service.remove_from_queued(event_info.account_id, event_info.exec_command)
                app_logger.log_debug("Event processed successfully, removed from active events", event_info)
            else:
                app_logger.log_error(f"Command failed: {result.error}", event_info)
                await self._handle_failed_event(event_info, result.error)
                
        except Exception as e:
            app_logger.log_error(f"Error processing event {event_info.event_id}: {e}", event_info)
            await self._handle_failed_event(event_info, str(e))
    
    async def _handle_failed_event(self, event_info: EventInfo, error_message: str):
        """Handle failed events by requeuing them automatically"""
        try:
            notification_service = self.service_container.get_notification_service()
            
            # Determine error type for notification
            error_type = 'event_connection_error' if 'connection' in error_message.lower() or 'timeout' in error_message.lower() else 'event_critical_error'
            await self._send_event_notification(notification_service, event_info, error_type, {'error_message': error_message})
            
            # Failure tracking now handled in Redis only
            
            # Update event status
            event_info.status = 'failed'
            
            # Requeue event automatically (goes to back of queue)
            queue_service = self.service_container.get_queue_service()
            updated_event_info = await queue_service.requeue_event_retry(event_info, notification_service)
            
            app_logger.log_info(f"Event requeued after failure: {error_message}", updated_event_info)
            
        except Exception as e:
            app_logger.log_error(f"Failed to requeue event {event_info.event_id}: {e}", event_info)
    
    async def _handle_permanent_failure(self, event_info: EventInfo, error_message: str):
        """Handle permanent failures by discarding event and logging error"""
        try:
            notification_service = self.service_container.get_notification_service()
            await self._send_event_notification(notification_service, event_info, 'event_critical_error', {'error_message': error_message})
            
            # Remove from active events (no requeue)
            queue_service = self.service_container.get_queue_service()
            await queue_service.remove_from_queued(event_info.account_id, event_info.exec_command)
            
            # Update event status
            event_info.status = 'failed'
            
            app_logger.log_error(f"Permanent failure - event discarded: {error_message}", event_info)
            
        except Exception as e:
            app_logger.log_error(f"Failed to handle permanent failure for event {event_info.event_id}: {e}", event_info)
    
    async def _retry_event_processor(self):
        """Background task to process retry events periodically"""
        app_logger.log_info("Starting retry event processor")
        queue_service = self.service_container.get_queue_service()
        
        while self.running:
            try:
                await asyncio.sleep(config.processing.retry_check_interval)
                if self.running:  # Check again after sleep
                    await queue_service.process_retry_events()
            except asyncio.CancelledError:
                app_logger.log_info("Retry event processor cancelled")
                break
            except Exception as e:
                app_logger.log_error(f"Error in retry event processor: {e}")
                # Continue running even if there's an error
                await asyncio.sleep(10)
        
        app_logger.log_info("Retry event processor stopped")
    
    async def _delayed_event_processor(self):
        """Background task to process delayed events periodically"""
        app_logger.log_info("Starting delayed event processor")
        queue_service = self.service_container.get_queue_service()
        
        while self.running:
            try:
                # Check every minute for delayed events ready for execution
                await asyncio.sleep(60)
                if self.running:  # Check again after sleep
                    await queue_service.process_delayed_events()
            except asyncio.CancelledError:
                app_logger.log_info("Delayed event processor cancelled")
                break
            except Exception as e:
                app_logger.log_error(f"Error in delayed event processor: {e}")
                # Continue running even if there's an error
                await asyncio.sleep(10)
        
        app_logger.log_info("Delayed event processor stopped")
    
    async def _send_event_notification(self, notification_service, event_info: EventInfo, event_type: str, extra_details: Dict[str, Any] = None):
        """Send notification for an event"""
        try:
            # Route to appropriate notification method based on event type
            if event_type == 'event_started':
                await notification_service.notify_event_started(event_info)
            elif event_type == 'event_success_first':
                await notification_service.notify_event_completed(event_info)
            elif event_type == 'event_success_retry':
                await notification_service.notify_event_completed_with_retry(event_info)
            elif event_type == 'event_delayed':
                delayed_until = event_info.payload.get('delayed_until', 'unknown')
                await notification_service.notify_event_execution_delayed(event_info, delayed_until)
            elif event_type == 'event_retry':
                await notification_service.notify_event_will_retry(event_info)  
            elif event_type == 'event_connection_error':
                error_message = extra_details.get('error_message') if extra_details else None
                await notification_service.notify_event_connection_error(event_info, error_message)
            elif event_type == 'event_critical_error':
                error_message = extra_details.get('error_message') if extra_details else None
                await notification_service.notify_event_critical_error(event_info, error_message)
            else:
                app_logger.log_warning(f"Unknown event type for notification: {event_type}")
            
        except Exception as e:
            app_logger.log_warning(f"Failed to send notification: {e}")
    
    async def _process_event_with_semaphore(self, event_info: EventInfo):
        """Process event with semaphore to limit concurrency"""
        async with self.semaphore:
            app_logger.log_debug(f"Acquired semaphore for event: {event_info.event_id}", event_info)
            try:
                await self.process_event(event_info)
            finally:
                app_logger.log_debug(f"Released semaphore for event: {event_info.event_id}", event_info)