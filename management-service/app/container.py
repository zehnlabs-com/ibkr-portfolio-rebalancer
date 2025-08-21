"""
Dependency injection container using dependency-injector framework
"""
from dependency_injector import containers, providers
from app.config import config
from app.services.redis_data_service import RedisDataService
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
from app.services.notification_monitor_service import NotificationMonitorService
from app.services.realtime_update_service import RealtimeUpdateService
from app.services.docker_event_service import DockerEventService
from app.handlers.websocket_handlers import get_websocket_manager


class ApplicationContainer(containers.DeclarativeContainer):
    """DI Container for Management Service using dependency-injector"""
    
    # Configuration is already loaded from config.yaml
    # No need for providers.Configuration() since we use the config directly
    
    # Focused Redis services (replacing monolithic RedisDataService)
    redis_queue_service = providers.Singleton(
        lambda: __import__('app.services.redis_queue_service', fromlist=['RedisQueueService']).RedisQueueService(config.redis_url)
    )
    
    redis_notification_service = providers.Singleton(
        lambda: __import__('app.services.redis_notification_service', fromlist=['RedisNotificationService']).RedisNotificationService(config.redis_url)
    )
    
    redis_account_service = providers.Singleton(
        lambda: __import__('app.services.redis_account_service', fromlist=['RedisAccountService']).RedisAccountService(config.redis_url)
    )
    
    # Legacy Redis data service (for backward compatibility during transition)
    redis_data_service = providers.Singleton(
        lambda: RedisDataService(config.redis_url)
    )
    
    # Repositories
    queue_repository = providers.Singleton(
        RedisQueueRepository,
        redis_data_service=redis_data_service
    )
    
    health_repository = providers.Singleton(
        RedisHealthRepository,
        redis_data_service=redis_data_service
    )
    
    # Services
    queue_service = providers.Singleton(
        QueueService,
        queue_repository=queue_repository
    )
    
    health_service = providers.Singleton(
        HealthService,
        health_repository=health_repository,
        queue_repository=queue_repository
    )
    
    # Handlers
    queue_handlers = providers.Singleton(
        QueueHandlers,
        queue_service=queue_service
    )
    
    health_handlers = providers.Singleton(
        HealthHandlers,
        health_service=health_service
    )
    
    dashboard_handlers = providers.Singleton(
        DashboardHandlers,
        redis_data_service=redis_data_service
    )
    
    docker_handlers = providers.Singleton(DockerHandlers)
    config_handlers = providers.Singleton(ConfigHandlers)
    strategies_handlers = providers.Singleton(StrategiesHandlers)
    
    websocket_handlers = providers.Singleton(
        WebSocketHandlers,
        dashboard_handlers=dashboard_handlers
    )
    
    notification_handlers = providers.Singleton(
        NotificationHandlers,
        redis_data_service=redis_data_service
    )
    
    
    # Singleton instances for shared services
    websocket_manager = providers.Singleton(get_websocket_manager)
    
    notification_cleanup_service = providers.Singleton(
        NotificationCleanupService,
        redis_data_service=redis_data_service
    )
    
    notification_monitor_service = providers.Singleton(
        NotificationMonitorService,
        redis_data_service=redis_data_service,
        websocket_manager=websocket_manager
    )
    
    realtime_update_service = providers.Singleton(
        RealtimeUpdateService,
        redis_data_service=redis_data_service,
        websocket_manager=websocket_manager
    )
    
    docker_event_service = providers.Singleton(
        DockerEventService,
        websocket_manager=websocket_manager,
        docker_handlers=docker_handlers
    )


# Legacy class wrapper for backward compatibility
class Container:
    """Legacy container wrapper for backward compatibility"""
    
    def __init__(self):
        self._container = ApplicationContainer()
        # Expose services as attributes for backward compatibility
        self.redis_data_service = self._container.redis_data_service()
        self.queue_repository = self._container.queue_repository()
        self.health_repository = self._container.health_repository()
        self.queue_service = self._container.queue_service()
        self.health_service = self._container.health_service()
        self.queue_handlers = self._container.queue_handlers()
        self.health_handlers = self._container.health_handlers()
        self.dashboard_handlers = self._container.dashboard_handlers()
        self.docker_handlers = self._container.docker_handlers()
        self.config_handlers = self._container.config_handlers()
        self.websocket_handlers = self._container.websocket_handlers()
        self.strategies_handlers = self._container.strategies_handlers()
        self.notification_handlers = self._container.notification_handlers()
        self.notification_cleanup_service = self._container.notification_cleanup_service()
        self.notification_monitor_service = self._container.notification_monitor_service()
        self.realtime_update_service = self._container.realtime_update_service()
        self.docker_event_service = self._container.docker_event_service()
    
    async def startup(self):
        """Initialize connections"""
        await self.redis_data_service.connect()
        await self.notification_cleanup_service.start()
        await self.notification_monitor_service.start()
        await self.realtime_update_service.start()
        await self.docker_event_service.start_event_stream()
    
    async def shutdown(self):
        """Clean up connections"""
        await self.docker_event_service.stop_event_stream()
        await self.realtime_update_service.stop()
        await self.notification_monitor_service.stop()
        await self.notification_cleanup_service.stop()
        await self.redis_data_service.disconnect()


# Global container instance
container = Container()