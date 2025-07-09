"""
Dependency injection container
"""
from app.config.settings import settings
from app.repositories.redis_queue_repository import RedisQueueRepository
from app.repositories.redis_health_repository import RedisHealthRepository
from app.services.queue_service import QueueService
from app.services.health_service import HealthService
from app.services.auth_service import AuthenticationService
from app.middleware.auth_middleware import AuthenticationMiddleware
from app.handlers.queue_handlers import QueueHandlers
from app.handlers.health_handlers import HealthHandlers


class Container:
    """Dependency injection container"""
    
    def __init__(self):
        # Repositories
        self.queue_repository = RedisQueueRepository(settings.redis_url)
        self.health_repository = RedisHealthRepository(settings.redis_url)
        
        # Services
        self.queue_service = QueueService(self.queue_repository)
        self.health_service = HealthService(self.health_repository, self.queue_repository)
        self.auth_service = AuthenticationService(settings.management_api_key)
        
        # Middleware
        self.auth_middleware = AuthenticationMiddleware(self.auth_service)
        
        # Handlers
        self.queue_handlers = QueueHandlers(self.queue_service, self.auth_middleware)
        self.health_handlers = HealthHandlers(self.health_service)
    
    async def startup(self):
        """Initialize connections"""
        await self.queue_repository.connect()
        await self.health_repository.connect()
    
    async def shutdown(self):
        """Clean up connections"""
        await self.queue_repository.disconnect()
        await self.health_repository.disconnect()


# Global container instance
container = Container()