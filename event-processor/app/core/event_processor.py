"""
Refactored event processor using command pattern.
"""

import asyncio
from typing import Dict, Any
from app.core.service_container import ServiceContainer
from app.commands.base import CommandStatus
from app.config import config
from app.logger import setup_logger

logger = setup_logger(__name__)


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
                event_data = await queue_service.get_next_event()
                
                if event_data:
                    logger.debug(f"Processing event: {event_data.get('event_id')}")
                    await self.process_event(event_data)
                else:
                    logger.debug("No events available, waiting...")
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(10)
    
    async def process_event(self, event_data: Dict[str, Any]):
        """Process a single event using command pattern"""
        event_id = event_data.get('event_id')
        account_id = event_data.get('account_id')
        data = event_data.get('data', {})
        exec_command = data.get('exec')
        times_queued = event_data.get('times_queued')
        
        if times_queued is None:
            await self._handle_permanent_failure(event_data, "Event missing required 'times_queued' field")
            return
        
        logger.info(f"Processing {exec_command} event for account {account_id} (attempt {times_queued})", extra={
            'event_id': event_id, 
            'account_id': account_id,
            'exec_command': exec_command,
            'times_queued': times_queued
        })
        
        queue_service = self.service_container.get_queue_service()
        try:
            # Times queued tracking now handled in Redis only
            
            # Get command factory and create command
            command_factory = self.service_container.get_command_factory()
            command = command_factory.create_command(exec_command, event_id, account_id, event_data)
            
            if not command:
                await self._handle_permanent_failure(event_data, f"No command handler found for: {exec_command}")
                return
            
            # Execute command with services
            services = self.service_container.get_services()
            result = await command.execute(services)
            
            # Handle command result
            if result.status == CommandStatus.SUCCESS:
                logger.info(f"Command executed successfully: {result.message}", extra={
                    'event_id': event_id,
                    'account_id': account_id,
                    'command_type': exec_command,
                    'times_queued': times_queued
                })
                
                # Remove from active events set after successful processing
                await queue_service.remove_from_queued(account_id, exec_command)
                logger.debug(f"Event processed successfully, removed from active events", extra={
                    'event_id': event_id,
                    'account_id': account_id,
                    'exec_command': exec_command
                })
            else:
                logger.error(f"Command failed: {result.error}", extra={
                    'event_id': event_id,
                    'account_id': account_id,
                    'command_type': exec_command,
                    'times_queued': times_queued
                })
                await self._handle_failed_event(event_data, result.error)
                
        except Exception as e:
            logger.error(f"Error processing event {event_id}: {e}", extra={
                'event_id': event_id,
                'account_id': account_id,
                'error': str(e),
                'times_queued': times_queued
            })
            await self._handle_failed_event(event_data, str(e))
    
    async def _handle_failed_event(self, event_data: Dict[str, Any], error_message: str):
        """Handle failed events by requeuing them automatically"""
        event_id = event_data.get('event_id')
        account_id = event_data.get('account_id')
        exec_command = event_data.get('data', {}).get('exec')
        times_queued = event_data.get('times_queued')
        if times_queued is None:
            logger.error(f"Event missing required 'times_queued' field, cannot handle failure for account {account_id}", extra={
                'event_id': event_id,
                'account_id': account_id,
                'event_data': event_data
            })
            return
        
        try:
            # Failure tracking now handled in Redis only
            
            # Requeue event automatically (goes to back of queue)
            queue_service = self.service_container.get_queue_service()
            await queue_service.requeue_event_delayed(event_data)
            
            logger.info(f"Event requeued after failure", extra={
                'event_id': event_id,
                'account_id': account_id,
                'exec_command': exec_command,
                'times_queued': times_queued + 1,
                'error': error_message
            })
            
        except Exception as e:
            logger.error(f"Failed to requeue event {event_id}: {e}", extra={
                'event_id': event_id,
                'account_id': account_id,
                'requeue_error': str(e)
            })
    
    async def _handle_permanent_failure(self, event_data: Dict[str, Any], error_message: str):
        """Handle permanent failures by discarding event and logging error"""
        event_id = event_data.get('event_id')
        account_id = event_data.get('account_id')
        exec_command = event_data.get('data', {}).get('exec')
        
        try:
            # Remove from active events (no requeue)
            queue_service = self.service_container.get_queue_service()
            await queue_service.remove_from_queued(account_id, exec_command)
            
            logger.error(f"Permanent failure - event discarded: {error_message}", extra={
                'event_id': event_id,
                'account_id': account_id,
                'exec_command': exec_command,
                'permanent_failure': True,
                'error': error_message
            })
            
        except Exception as e:
            logger.error(f"Failed to handle permanent failure for event {event_id}: {e}", extra={
                'event_id': event_id,
                'account_id': account_id,
                'permanent_failure_error': str(e)
            })
    
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