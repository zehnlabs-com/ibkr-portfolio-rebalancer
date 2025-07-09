"""
Application service for managing application lifecycle.
"""

from app.core.service_container import ServiceContainer
from app.core.signal_handler import SignalHandler
from app.logger import setup_logger

logger = setup_logger(__name__)


class ApplicationService:
    """Service for managing application lifecycle and orchestration"""
    
    def __init__(self):
        self.service_container = ServiceContainer()
        self.signal_handler = SignalHandler(self.stop)
        self.running = False
    
    async def start(self):
        """Start the application services"""
        logger.info("Starting application services...")
        
        try:
            # Initialize service container
            self.service_container.initialize()
            
            # Set up signal handlers
            self.signal_handler.setup_signal_handlers()
            
            self.running = True
            logger.info("Application services started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start application services: {e}")
            raise
    
    async def stop(self):
        """Stop the application services"""
        if not self.running:
            return            
        
        self.running = False

        logger.info("Application services stopped successfully")
        
    
    def get_service_container(self) -> ServiceContainer:
        """Get the service container"""
        return self.service_container
    
    def is_running(self) -> bool:
        """Check if application is running"""
        return self.running