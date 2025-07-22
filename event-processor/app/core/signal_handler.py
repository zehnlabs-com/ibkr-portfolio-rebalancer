"""
Signal handler for graceful shutdown.
"""

import signal
import asyncio
from typing import Callable, Awaitable
from app.logger import AppLogger

app_logger = AppLogger(__name__)


class SignalHandler:
    """Handler for system signals with graceful shutdown support"""
    
    def __init__(self, shutdown_callback: Callable[[], Awaitable[None]]):
        self.shutdown_callback = shutdown_callback
        self._shutdown_initiated = False
    
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        def signal_handler(sig_num, frame):
            if self._shutdown_initiated:
                app_logger.log_warning("Shutdown already initiated, ignoring signal")
                return
                
            app_logger.log_info(f"Received signal {sig_num}")
            self._shutdown_initiated = True
            
            # Create new event loop if none exists
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Schedule the shutdown
            signal_name = signal.Signals(sig_num).name
            asyncio.create_task(self._handle_shutdown(signal_name))
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        app_logger.log_info("Signal handlers registered")
    
    async def _handle_shutdown(self, signal_name: str):
        """Handle shutdown process"""
        app_logger.log_info(f"Received {signal_name} signal, initiating graceful shutdown...")
        
        try:
            await self.shutdown_callback()
            app_logger.log_info("Graceful shutdown completed")
        except Exception as e:
            app_logger.log_error(f"Error during shutdown: {e}")
            raise