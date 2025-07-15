"""
Refactored event processor using command pattern.
"""

import asyncio
from typing import Dict, Any
from app.core.service_container import ServiceContainer
from app.commands.base import CommandStatus
from app.models.events import EventInfo
from app.config import config
from app.logger import setup_logger, EventLogger

logger = setup_logger(__name__)
event_logger = EventLogger(__name__)


class EventProcessor:
    """Main event processing class using command pattern"""
    
    def __init__(self, service_container: ServiceContainer):
        self.service_container = service_container
        self.running = False
        self.delayed_processor_task = None
    
    async def start_processing(self):
        """Start the event processing loop"""
        logger.info("Starting event processing loop...")
        
        try:
            self.running = True
            logger.info("Event processing loop started successfully")
            
            # Start delayed event processor task
            self.delayed_processor_task = asyncio.create_task(self._delayed_event_processor())
            
            # Start main processing loop
            await self._main_loop()
            
        except Exception as e:
            logger.error(f"Failed to start event processing loop: {e}")
            raise
    
    async def stop_processing(self):
        """Stop the event processing loop"""
        if not self.running:
            return
            
        logger.info("Stopping event processing loop...")
        self.running = False
        
        # Cancel delayed processor task
        if self.delayed_processor_task and not self.delayed_processor_task.done():
            self.delayed_processor_task.cancel()
            try:
                await self.delayed_processor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Event processing loop stopped")
    
    async def _main_loop(self):
        """Main event processing loop"""
        logger.info("Starting main processing loop")
        
        queue_service = self.service_container.get_queue_service()
        
        while self.running:
            try:
                logger.debug("Checking for events in queue...")
                # Get event from queue with timeout
                event_info = await queue_service.get_next_event()
                
                if event_info:
                    logger.debug(f"Processing event: {event_info.event_id}")
                    await self.process_event(event_info)
                else:
                    logger.debug("No events available, waiting...")
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(10)
    
    async def process_event(self, event_info: EventInfo):
        """Process a single event using command pattern"""
        event_logger.log_debug("Processing event", event_info)
        
        queue_service = self.service_container.get_queue_service()
        try:
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
                event_logger.log_info(f"Command executed successfully: {result.message}", event_info)
                
                # Remove from active events set after successful processing
                await queue_service.remove_from_queued(event_info.account_id, event_info.exec_command)
                event_logger.log_debug("Event processed successfully, removed from active events", event_info)
            else:
                event_logger.log_error(f"Command failed: {result.error}", event_info)
                await self._handle_failed_event(event_info, result.error)
                
        except Exception as e:
            event_logger.log_error(f"Error processing event {event_info.event_id}: {e}", event_info)
            await self._handle_failed_event(event_info, str(e))
    
    async def _handle_failed_event(self, event_info: EventInfo, error_message: str):
        """Handle failed events by requeuing them automatically"""
        try:
            # Failure tracking now handled in Redis only
            
            # Update event status
            event_info.status = 'failed'
            
            # Requeue event automatically (goes to back of queue)
            queue_service = self.service_container.get_queue_service()
            updated_event_info = await queue_service.requeue_event_delayed(event_info)
            
            event_logger.log_info(f"Event requeued after failure: {error_message}", updated_event_info)
            
        except Exception as e:
            event_logger.log_error(f"Failed to requeue event {event_info.event_id}: {e}", event_info)
    
    async def _handle_permanent_failure(self, event_info: EventInfo, error_message: str):
        """Handle permanent failures by discarding event and logging error"""
        try:
            # Remove from active events (no requeue)
            queue_service = self.service_container.get_queue_service()
            await queue_service.remove_from_queued(event_info.account_id, event_info.exec_command)
            
            # Update event status
            event_info.status = 'failed'
            
            event_logger.log_error(f"Permanent failure - event discarded: {error_message}", event_info)
            
        except Exception as e:
            event_logger.log_error(f"Failed to handle permanent failure for event {event_info.event_id}: {e}", event_info)
    
    async def _delayed_event_processor(self):
        """Background task to process delayed events periodically"""
        logger.info("Starting delayed event processor")
        queue_service = self.service_container.get_queue_service()
        
        while self.running:
            try:
                await asyncio.sleep(config.processing.retry_check_interval)
                if self.running:  # Check again after sleep
                    await queue_service.process_delayed_events()
            except asyncio.CancelledError:
                logger.info("Delayed event processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in delayed event processor: {e}")
                # Continue running even if there's an error
                await asyncio.sleep(10)
        
        logger.info("Delayed event processor stopped")