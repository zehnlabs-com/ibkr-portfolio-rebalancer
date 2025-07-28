"""
Service container for dependency injection.
"""

from typing import Dict, Any, Optional, TypeVar, Type
from app.services.queue_service import QueueService
from app.services.ibkr_client import IBKRClient
from app.services.notification_service import NotificationService
from app.commands.factory import CommandFactory
from app.logger import AppLogger

app_logger = AppLogger(__name__)

T = TypeVar('T')


class ServiceContainer:
    """Container for managing service dependencies and their lifecycle"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._initialized = False
    
    def initialize(self):
        """Initialize all services with their dependencies"""
        if self._initialized:
            return
            
        app_logger.log_info("Initializing service container...")
        
        # Initialize core services
        self._services['queue_service'] = QueueService()
        self._services['ibkr_client'] = IBKRClient()
        self._services['notification_service'] = NotificationService()
        self._services['command_factory'] = CommandFactory()
        
        # Initialize rebalancer service with dependencies
        # Import here to avoid circular dependencies
        try:
            from app.services.rebalancer_service import RebalancerService
            self._services['rebalancer_service'] = RebalancerService(self._services['ibkr_client'])
            app_logger.log_info("Rebalancer services initialized successfully")
        except Exception as e:
            app_logger.log_error(f"CRITICAL: Could not initialize rebalancer services: {e}")
            app_logger.log_error("Application cannot proceed without real financial services")
            raise RuntimeError(f"Failed to initialize critical financial services: {e}")
        
        self._initialized = True
        app_logger.log_info("Service container initialized successfully")
    
    def get_service(self, service_name: str) -> Optional[Any]:
        """Get a service by name"""
        if not self._initialized:
            raise RuntimeError("Service container not initialized")
        
        return self._services.get(service_name)
    
    def get_services(self) -> Dict[str, Any]:
        """Get all services as a dictionary"""
        if not self._initialized:
            raise RuntimeError("Service container not initialized")
        
        return self._services.copy()
    
    def register_service(self, service_name: str, service_instance: Any):
        """Register a custom service instance"""
        self._services[service_name] = service_instance
        app_logger.log_debug(f"Registered service: {service_name}")
    
    def get_queue_service(self) -> QueueService:
        """Get the queue service instance"""
        return self.get_service('queue_service')
    
    
    def get_ibkr_client(self) -> IBKRClient:
        """Get the IBKR client instance"""
        return self.get_service('ibkr_client')
    
    def get_command_factory(self) -> CommandFactory:
        """Get the command factory instance"""
        return self.get_service('command_factory')
    
    def get_notification_service(self) -> NotificationService:
        """Get the notification service instance"""
        return self.get_service('notification_service')
    
    def is_initialized(self) -> bool:
        """Check if container is initialized"""
        return self._initialized