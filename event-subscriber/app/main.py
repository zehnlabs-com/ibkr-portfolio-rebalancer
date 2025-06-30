"""
Event Subscriber Service - Main Application Entry Point

This service subscribes to Ably events and triggers rebalancing operations
via HTTP calls to the Rebalancer API Service.
"""
import asyncio
import signal
import sys
from app.config import config
from app.logger import setup_logger
from app.services.ably_service import AblyEventSubscriber

logger = setup_logger(__name__, level=config.LOG_LEVEL)


class EventSubscriberApp:
    """Main application class for the Event Subscriber Service"""
    
    def __init__(self):
        self.ably_subscriber = AblyEventSubscriber()
        self.running = False
        
    async def start(self):
        """Start the Event Subscriber Service"""
        try:
            logger.info("Starting Event Subscriber Service...")
            
            # Start the Ably event subscriber
            await self.ably_subscriber.start()
            
            self.running = True
            logger.info("Event Subscriber Service started successfully")
            
            # Keep the service running
            await self._run_forever()
            
        except Exception as e:
            logger.error(f"Failed to start Event Subscriber Service: {e}")
            raise
    
    async def stop(self):
        """Stop the Event Subscriber Service"""
        if not self.running:
            return
            
        logger.info("Stopping Event Subscriber Service...")
        self.running = False
        
        try:
            await self.ably_subscriber.stop()
            logger.info("Event Subscriber Service stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping Event Subscriber Service: {e}")
    
    async def _run_forever(self):
        """Keep the service running and handle graceful shutdown"""
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Service shutdown requested")
            await self.stop()
    
    async def get_status(self):
        """Get current status of the service"""
        return await self.ably_subscriber.get_status()


# Global app instance
app = EventSubscriberApp()


async def shutdown_handler(sig_name):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received {sig_name} signal, initiating graceful shutdown...")
    await app.stop()


def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown"""
    def signal_handler(sig_num, frame):
        logger.info(f"Received signal {sig_num}")
        # Create new event loop if none exists
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Schedule the shutdown
        asyncio.create_task(shutdown_handler(signal.Signals(sig_num).name))
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point"""
    try:
        # Set up signal handlers
        setup_signal_handlers()
        
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