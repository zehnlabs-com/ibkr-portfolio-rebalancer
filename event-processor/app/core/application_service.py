"""
Application service for managing application lifecycle.
"""

from app.core.service_container import ServiceContainer
from app.core.signal_handler import SignalHandler
from app.logger import AppLogger

app_logger = AppLogger(__name__)


class ApplicationService:
    """Service for managing application lifecycle and orchestration"""
    
    def __init__(self):
        self.service_container = ServiceContainer()
        self.signal_handler = SignalHandler(self.stop)
        self.running = False
    
    async def start(self):
        """Start the application services"""
        app_logger.log_info("Starting application services...")
        
        try:
            # Initialize service container
            self.service_container.initialize()
            
            # Set up signal handlers
            self.signal_handler.setup_signal_handlers()
            
            # Recover any events stuck in active_events_set from previous service restart
            queue_service = self.service_container.get_queue_service()
            recovered_count = await queue_service.recover_stuck_active_events()
            if recovered_count > 0:
                app_logger.log_info(f"Startup recovery completed: {recovered_count} events recovered")
            
            self.running = True
            app_logger.log_info("Application services started successfully")
            
        except Exception as e:
            app_logger.log_error(f"Failed to start application services: {e}")
            raise
    
    async def stop(self):
        """Stop the application services"""
        if not self.running:
            return            
        
        self.running = False

        app_logger.log_info("Application services stopped successfully")
        
    
    def get_service_container(self) -> ServiceContainer:
        """Get the service container"""
        return self.service_container
    
    def is_running(self) -> bool:
        """Check if application is running"""
        return self.running