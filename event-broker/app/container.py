"""
Dependency injection container for Event Broker service using dependency-injector
"""
from dependency_injector import containers, providers
from app.services.redis_queue_service import RedisQueueService
from app.services.queue_service import QueueService
from app.services.ably_service import AblyEventSubscriber


class Container(containers.DeclarativeContainer):
    """DI Container for Event Broker service"""
    
    # Configuration
    config = providers.Configuration()
    config.redis_url.from_env("REDIS_URL", default="redis://redis:6379/0")
    
    # Redis Services (Singletons)
    redis_queue_service = providers.Singleton(
        RedisQueueService,
        redis_url=config.redis_url
    )
    
    
    # Business Services
    queue_service = providers.Singleton(
        QueueService,
        redis_queue_service=redis_queue_service
    )
    
    ably_subscriber = providers.Singleton(
        AblyEventSubscriber,
        queue_service=queue_service
    )