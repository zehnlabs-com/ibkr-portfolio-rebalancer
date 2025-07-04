"""
Event Processor - Main Application Entry Point

This service processes rebalance events from Redis queue and executes them via IBKR.
"""
import nest_asyncio
# Apply nest_asyncio BEFORE any other async imports to prevent event loop conflicts
nest_asyncio.apply()

import asyncio
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Any
from app.config import config
from app.logger import setup_logger, log_with_event
from app.database import db_manager
from app.services.queue_service import QueueService
from app.services.event_service import EventService
from app.services.market_hours import MarketHoursService
from app.services.ibkr_client import IBKRClient
from app.services.rebalancer_service import RebalancerService

logger = setup_logger(__name__)


class EventProcessor:
    """Main event processing class"""
    
    def __init__(self):
        self.queue_service = QueueService()
        self.event_service = EventService()
        self.market_hours_service = MarketHoursService()
        self.ibkr_client = IBKRClient()
        self.rebalancer_service = RebalancerService(self.ibkr_client)
        self.running = False
        
    async def start(self):
        """Start the event processor"""
        logger.info("Starting Event Processor...")

        await asyncio.sleep(config.processing.startup_initial_delay); # Initial delay to allow other services to start
        
        try:
            # Connect to IBKR with startup retry logic
            connected = False
            for attempt in range(config.processing.startup_max_attempts):
                try:
                    logger.info(f"IBKR connection attempt {attempt + 1}/{config.processing.startup_max_attempts}")
                    
                    if await self.ibkr_client.connect():
                        # Test market data readiness
                        try:
                            test_prices = await self.ibkr_client.get_multiple_market_prices(['SPY'])
                            if test_prices:
                                logger.info("Market data is ready")
                                connected = True
                                break
                            else:
                                logger.warning("Market data test failed - no prices returned, retrying...")
                        except Exception as e:
                            logger.warning(f"Market data not ready: {e}")
                    
                    # If we get here, connection failed or market data not ready
                    if attempt < config.processing.startup_max_attempts - 1:
                        logger.info(f"Waiting {config.processing.startup_delay} seconds before next attempt...")
                        await asyncio.sleep(config.processing.startup_delay)
                    
                except Exception as e:
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                    if attempt < config.processing.startup_max_attempts - 1:
                        logger.info(f"Waiting {config.processing.startup_delay} seconds before next attempt...")
                        await asyncio.sleep(config.processing.startup_delay)
            
            if not connected:
                logger.error("Failed to establish IBKR connection after all attempts, exiting")
                return
            
            self.running = True
            logger.info("Event Processor started successfully")
            
            # Start main processing loop
            await self._main_loop()
            
        except Exception as e:
            logger.error(f"Failed to start Event Processor: {e}")
            raise
    
    async def stop(self):
        """Stop the event processor"""
        if not self.running:
            return
            
        logger.info("Stopping Event Processor...")
        self.running = False
        
        try:
            # Disconnect from IBKR
            await self.ibkr_client.disconnect()
            
            # Close database connection pool
            await db_manager.close_connection_pool()
            
            logger.info("Event Processor stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping Event Processor: {e}")
    
    async def _main_loop(self):
        """Main event processing loop"""
        logger.info("Starting main processing loop")
        
        while self.running:
            try:
                # Check if markets are open
                if not await self.market_hours_service.is_market_open():
                    logger.debug("Markets closed, waiting...")
                    await asyncio.sleep(300)  # Wait 5 minutes
                    continue
                
                # Get next event from queue
                event_data = self.queue_service.get_next_event()
                
                if event_data:
                    await self.process_event(event_data)
                else:
                    # No events in queue, short sleep
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def process_event(self, event_data: Dict[str, Any]):
        """Process a single event"""
        event_id = event_data.get('event_id')
        account_id = event_data.get('account_id')
        start_time = time.time()
        
        try:
            log_with_event(logger, 'info', 
                          f"Processing event for account {account_id}",
                          event_id=event_id, account_id=account_id)
            
            # Update event status to processing
            await self.event_service.update_status(event_id, 'processing')
            
            # Remove from queued accounts set
            self.queue_service.remove_from_queued(account_id)
            
            # Get account configuration
            account_config = config.get_account_config(account_id)
            if not account_config:
                raise ValueError(f"No configuration found for account {account_id}")
            
            # Determine order type based on market timing
            order_type = await self.market_hours_service.get_order_type()
            
            log_with_event(logger, 'info',
                          f"Using order type: {order_type}",
                          event_id=event_id, account_id=account_id)
            
            # Execute rebalancing
            result = await self.rebalancer_service.rebalance_account(
                account_config, 
                order_type
            )
            
            # Update event status to completed
            await self.event_service.update_status(event_id, 'completed')
            
            processing_time = time.time() - start_time
            
            log_with_event(logger, 'info',
                          f"Event processed successfully - orders: {len(result.orders)}, time: {processing_time:.2f}s",
                          event_id=event_id, account_id=account_id,
                          orders_placed=len(result.orders), processing_time=processing_time)
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_message = str(e)
            
            log_with_event(logger, 'error',
                          f"Event processing failed: {error_message}",
                          event_id=event_id, account_id=account_id,
                          processing_time=processing_time)
            
            # Handle retry logic
            await self.handle_failed_event(event_id, account_id, event_data, error_message)
    
    async def handle_failed_event(self, event_id: str, account_id: str, 
                                 event_data: Dict[str, Any], error_message: str):
        """Handle failed event with retry logic"""
        try:
            # Update event status to failed
            await self.event_service.update_status(event_id, 'failed', error_message)
            
            # Increment retry count
            await self.event_service.increment_retry(event_id)
            
            # Check if should retry
            if await self.event_service.should_retry(event_id, config.processing.max_retry_days):
                # Put back in queue for retry
                self.queue_service.requeue_event(event_data)
                
                log_with_event(logger, 'info',
                              "Event requeued for retry",
                              event_id=event_id, account_id=account_id)
            else:
                log_with_event(logger, 'error',
                              "Event exceeded retry limit",
                              event_id=event_id, account_id=account_id)
                
        except Exception as e:
            log_with_event(logger, 'error',
                          f"Failed to handle failed event: {e}",
                          event_id=event_id, account_id=account_id)


# Global app instance
app = EventProcessor()


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