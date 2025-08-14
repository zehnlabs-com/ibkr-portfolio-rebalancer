"""
Dependency injection container
"""
from app.config.settings import settings
from app.repositories.redis_queue_repository import RedisQueueRepository
from app.repositories.redis_health_repository import RedisHealthRepository
from app.services.queue_service import QueueService
from app.services.health_service import HealthService
from app.handlers.queue_handlers import QueueHandlers
from app.handlers.health_handlers import HealthHandlers
from app.handlers.dashboard_handlers import DashboardHandlers
from app.handlers.docker_handlers import DockerHandlers
from app.handlers.config_handlers import ConfigHandlers
from app.handlers.websocket_handlers import WebSocketHandlers
from app.handlers.strategies_handlers import StrategiesHandlers
from app.handlers.notification_handlers import NotificationHandlers
from app.services.notification_cleanup_service import NotificationCleanupService
from app.services.realtime_update_service import RealtimeUpdateService
from app.handlers.websocket_handlers import get_websocket_manager


class Container:
    """Dependency injection container"""
    
    def __init__(self):
        # Repositories
        self.queue_repository = RedisQueueRepository(settings.redis_url)
        self.health_repository = RedisHealthRepository(settings.redis_url)
        
        # Services
        self.queue_service = QueueService(self.queue_repository)
        self.health_service = HealthService(self.health_repository, self.queue_repository)
        
        # Handlers
        self.queue_handlers = QueueHandlers(self.queue_service)
        self.health_handlers = HealthHandlers(self.health_service)
        self.dashboard_handlers = DashboardHandlers(self.queue_repository)
        self.docker_handlers = DockerHandlers()
        self.config_handlers = ConfigHandlers()
        self.websocket_handlers = WebSocketHandlers(self.dashboard_handlers)
        self.strategies_handlers = StrategiesHandlers()
        self.notification_handlers = NotificationHandlers(self.queue_repository.redis)
        self.notification_cleanup_service = NotificationCleanupService(self.queue_repository.redis)
        self.realtime_update_service = RealtimeUpdateService(settings.redis_url, get_websocket_manager())
    
    async def startup(self):
        """Initialize connections"""
        await self.queue_repository.connect()
        await self.health_repository.connect()
        await self.notification_cleanup_service.start()
        await self.realtime_update_service.start()
    
    async def shutdown(self):
        """Clean up connections"""
        await self.realtime_update_service.stop()
        await self.notification_cleanup_service.stop()
        await self.queue_repository.disconnect()
        await self.health_repository.disconnect()


# Global container instance
container = Container()