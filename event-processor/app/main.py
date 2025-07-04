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
                # Get next event from queue
                event_data = await self.queue_service.get_next_event()
                
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
        # Check both 'data' and 'payload' for backward compatibility
        data_payload = event_data.get('data', {})
        payload = event_data.get('payload', {})
        action = data_payload.get('exec') or payload.get('exec')
        
        if not action:
            raise ValueError("No exec specified in payload.")
        start_time = time.time()
        
        try:
            log_with_event(logger, 'info', 
                          f"Processing event for account {account_id}, action: {action}",
                          event_id=event_id, account_id=account_id, action=action)
            
            # Update event status to processing
            await self.event_service.update_status(event_id, 'processing')
            
            # Remove from queued accounts set
            await self.queue_service.remove_from_queued(account_id)
            
            # Get account configuration
            account_config = config.get_account_config(account_id)
            if not account_config:
                raise ValueError(f"No configuration found for account {account_id}")
            
            # Route to appropriate handler based on action
            result = await self.handle_action(action, account_config, event_id, account_id)
            
            # Update event status to completed
            await self.event_service.update_status(event_id, 'completed')
            
            processing_time = time.time() - start_time
            
            log_with_event(logger, 'info',
                          f"Event processed successfully - action: {action}, time: {processing_time:.2f}s",
                          event_id=event_id, account_id=account_id,
                          action=action, processing_time=processing_time)
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_message = str(e)
            
            log_with_event(logger, 'error',
                          f"Event processing failed: {error_message}",
                          event_id=event_id, account_id=account_id,
                          processing_time=processing_time)
            
            # Handle retry logic
            await self.handle_failed_event(event_id, account_id, event_data, error_message)
    
    async def handle_action(self, action: str, account_config, event_id: str, account_id: str):
        """Route to appropriate handler based on action type"""
        if action == 'rebalance':
            return await self.handle_rebalance(account_config, event_id, account_id)
        elif action == 'print-positions':
            return await self.handle_print_positions(account_config, event_id, account_id)
        elif action == 'cancel-orders':
            return await self.handle_cancel_orders(account_config, event_id, account_id)
        elif action == 'health':
            return await self.handle_health(account_config, event_id, account_id)
        elif action == 'print-equity':
            return await self.handle_print_equity(account_config, event_id, account_id)
        elif action == 'print-orders':
            return await self.handle_print_orders(account_config, event_id, account_id)
        elif action == 'print-rebalance':
            return await self.handle_print_rebalance(account_config, event_id, account_id)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def handle_rebalance(self, account_config, event_id: str, account_id: str):
        """Handle rebalance action - full rebalance with orders sent to broker"""
        
        # Check if markets are open for rebalance operations
        if not await self.market_hours_service.is_market_open():
            error_msg = "Markets are closed - rebalance operations not allowed"
            log_with_event(logger, 'error', error_msg, 
                          event_id=event_id, account_id=account_id)
            raise ValueError(error_msg)
        
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
        
        log_with_event(logger, 'info',
                      f"Rebalance completed - orders: {len(result.orders)}",
                      event_id=event_id, account_id=account_id,
                      orders_placed=len(result.orders))
        
        return result
    
    async def handle_print_positions(self, account_config, event_id: str, account_id: str):
        """Handle print-positions action - log all current positions"""
        log_with_event(logger, 'info',
                      f"Printing positions for account {account_id}",
                      event_id=event_id, account_id=account_id)
        
        positions = await self.ibkr_client.get_positions(account_id)
        
        if not positions:
            log_with_event(logger, 'info',
                          f"No positions found for account {account_id}",
                          event_id=event_id, account_id=account_id)
        else:
            log_with_event(logger, 'info',
                          f"Current positions for account {account_id}:",
                          event_id=event_id, account_id=account_id)
            
            for position in positions:
                log_with_event(logger, 'info',
                              f"  {position['symbol']}: {position['position']} shares, "
                              f"market value: ${position['market_value']:.2f}, "
                              f"avg cost: ${position['avg_cost']:.2f}",
                              event_id=event_id, account_id=account_id,
                              symbol=position['symbol'], position=position['position'],
                              market_value=position['market_value'], avg_cost=position['avg_cost'])
        
        return {"action": "print-positions", "positions": positions}
    
    async def handle_cancel_orders(self, account_config, event_id: str, account_id: str):
        """Handle cancel-orders action - cancel all pending orders"""
        log_with_event(logger, 'info',
                      f"Cancelling all pending orders for account {account_id}",
                      event_id=event_id, account_id=account_id)
        
        cancelled_orders = await self.ibkr_client.cancel_all_orders(account_id)
        
        if not cancelled_orders:
            log_with_event(logger, 'info',
                          f"No pending orders found for account {account_id}",
                          event_id=event_id, account_id=account_id)
        else:
            log_with_event(logger, 'info',
                          f"Cancelled {len(cancelled_orders)} orders for account {account_id}",
                          event_id=event_id, account_id=account_id,
                          cancelled_orders_count=len(cancelled_orders))
        
        return {"action": "cancel-orders", "cancelled_orders": cancelled_orders}
    
    async def handle_health(self, account_config, event_id: str, account_id: str):
        """Handle health action - log health status including IBKR connection"""
        log_with_event(logger, 'info',
                      f"Checking health status for account {account_id}",
                      event_id=event_id, account_id=account_id)
        
        # Check IBKR connection
        ibkr_connected = await self.ibkr_client.ensure_connected()
        
        # Check database connection
        db_connected = await self.event_service.is_connected()
        
        # Get some basic metrics
        try:
            account_value = await self.ibkr_client.get_account_value(account_id)
            account_accessible = True
        except Exception as e:
            account_value = None
            account_accessible = False
            log_with_event(logger, 'warning',
                          f"Cannot access account {account_id}: {e}",
                          event_id=event_id, account_id=account_id)
        
        health_status = {
            "ibkr_connected": ibkr_connected,
            "database_connected": db_connected,
            "account_accessible": account_accessible,
            "account_value": account_value
        }
        
        log_with_event(logger, 'info',
                      f"Health status for account {account_id}: "
                      f"IBKR connected: {ibkr_connected}, "
                      f"DB connected: {db_connected}, "
                      f"Account accessible: {account_accessible}, "
                      f"Account value: ${account_value:.2f}" if account_value else "Account value: N/A",
                      event_id=event_id, account_id=account_id,
                      **health_status)
        
        return {"action": "health", "status": health_status}
    
    async def handle_print_equity(self, account_config, event_id: str, account_id: str):
        """Handle print-equity action - log total account value"""
        log_with_event(logger, 'info',
                      f"Printing equity for account {account_id}",
                      event_id=event_id, account_id=account_id)
        
        account_value = await self.ibkr_client.get_account_value(account_id)
        
        log_with_event(logger, 'info',
                      f"Total account value for {account_id}: ${account_value:.2f}",
                      event_id=event_id, account_id=account_id,
                      account_value=account_value)
        
        return {"action": "print-equity", "account_value": account_value}
    
    async def handle_print_orders(self, account_config, event_id: str, account_id: str):
        """Handle print-orders action - log all pending orders"""
        log_with_event(logger, 'info',
                      f"Printing pending orders for account {account_id}",
                      event_id=event_id, account_id=account_id)
        
        # Get open orders by trying to cancel them without actually cancelling
        # We'll need to access the IBKR client's open orders method directly
        open_orders = self.ibkr_client.ib.openOrders()
        account_orders = [order for order in open_orders if order.account == account_id]
        
        if not account_orders:
            log_with_event(logger, 'info',
                          f"No pending orders found for account {account_id}",
                          event_id=event_id, account_id=account_id)
        else:
            log_with_event(logger, 'info',
                          f"Pending orders for account {account_id}:",
                          event_id=event_id, account_id=account_id)
            
            for order in account_orders:
                symbol = 'Unknown'
                if hasattr(order, 'contract') and order.contract:
                    symbol = getattr(order.contract, 'symbol', 'Unknown')
                
                log_with_event(logger, 'info',
                              f"  Order {order.orderId}: {order.action} {abs(order.totalQuantity)} "
                              f"{symbol} ({order.orderType})",
                              event_id=event_id, account_id=account_id,
                              order_id=order.orderId, action=order.action,
                              quantity=abs(order.totalQuantity), symbol=symbol,
                              order_type=order.orderType)
        
        # Format order details for return
        order_details = []
        for order in account_orders:
            symbol = 'Unknown'
            if hasattr(order, 'contract') and order.contract:
                symbol = getattr(order.contract, 'symbol', 'Unknown')
            
            order_details.append({
                'order_id': str(order.orderId),
                'symbol': symbol,
                'quantity': abs(order.totalQuantity),
                'action': order.action,
                'order_type': order.orderType
            })
        
        return {"action": "print-orders", "orders": order_details}
    
    async def handle_print_rebalance(self, account_config, event_id: str, account_id: str):
        """Handle print-rebalance action - calculate and log rebalance orders without executing"""
        log_with_event(logger, 'info',
                      f"Printing rebalance orders for account {account_id} (dry run)",
                      event_id=event_id, account_id=account_id)
        
        # Execute dry run rebalancing
        result = await self.rebalancer_service.dry_run_rebalance(account_config)
        
        if not result.orders:
            log_with_event(logger, 'info',
                          f"No rebalance orders needed for account {account_id}",
                          event_id=event_id, account_id=account_id)
        else:
            log_with_event(logger, 'info',
                          f"Rebalance orders for account {account_id} (would execute {len(result.orders)} orders):",
                          event_id=event_id, account_id=account_id,
                          orders_count=len(result.orders))
            
            for order in result.orders:
                log_with_event(logger, 'info',
                              f"  Would {order.action} {order.quantity} shares of {order.symbol} "
                              f"(${order.market_value:.2f})",
                              event_id=event_id, account_id=account_id,
                              action=order.action, quantity=order.quantity,
                              symbol=order.symbol, market_value=order.market_value)
        
        return {"action": "print-rebalance", "orders": result.orders, "equity_info": result.equity_info}
    
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
                await self.queue_service.requeue_event(event_data)
                
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