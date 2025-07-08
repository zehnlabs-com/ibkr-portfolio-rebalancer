"""
Event Processor - Main Application Entry Point

This service processes rebalance events from Redis queue and executes them via IBKR.
"""
import nest_asyncio
# Apply nest_asyncio BEFORE any other async imports to prevent event loop conflicts
nest_asyncio.apply()

import asyncio
import sys
from app.core import ApplicationService, EventProcessor
from app.logger import setup_logger

logger = setup_logger(__name__)


class EventProcessorApp:
    """Main application orchestrator"""
    
    def __init__(self):
        self.application_service = ApplicationService()
        self.event_processor = None
        
    async def start(self):
        """Start the event processor application"""
        logger.info("Starting Event Processor Application...")
        
        try:
            # Start application services
            await self.application_service.start()
            
            # Create event processor with service container
            service_container = self.application_service.get_service_container()
            self.event_processor = EventProcessor(service_container)
            
            # Start event processing
            await self.event_processor.start_processing()
            
        except Exception as e:
            logger.error(f"Failed to start Event Processor Application: {e}")
            raise
    
    async def stop(self):
        """Stop the event processor application"""
        logger.info("Stopping Event Processor Application...")
        
        try:
            # Stop event processing
            if self.event_processor:
                await self.event_processor.stop_processing()
            
            # Stop application services
            await self.application_service.stop()
            
            logger.info("Event Processor Application stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping Event Processor Application: {e}")


# Global app instance
app = EventProcessorApp()


async def main():
    """Main entry point"""
    try:
        # Start the application
        await app.start()
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        await app.stop()
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        await app.stop()
        sys.exit(1)


if __name__ == "__main__":
    # Run the application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)