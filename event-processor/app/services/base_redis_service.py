"""
Base Redis Service with resilience patterns for async operations
"""
import logging
from typing import Optional, Any
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_log,
    after_log
)

logger = logging.getLogger(__name__)


class BaseRedisService:
    """Base class for all Redis services with built-in resilience"""
    
    def __init__(self, redis_url: str, max_connections: int = 50, max_retries: int = 3):
        """
        Initialize base Redis service with connection pooling
        
        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
            max_connections: Maximum connections in pool
            max_retries: Maximum retry attempts for operations
        """
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.max_retries = max_retries
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
    
    def _get_connection_pool(self) -> ConnectionPool:
        """Get or create connection pool"""
        if self._pool is None:
            self._pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
                decode_responses=True
            )
        return self._pool
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((redis.ConnectionError, redis.TimeoutError)),
        before=before_log(logger, logging.DEBUG),
        after=after_log(logger, logging.DEBUG)
    )
    async def _get_client(self) -> redis.Redis:
        """
        Get Redis client with retry logic
        
        Returns:
            Connected Redis client
        """
        if self._client is None:
            pool = self._get_connection_pool()
            self._client = redis.Redis(connection_pool=pool)
            # Test connection
            await self._client.ping()
            logger.debug(f"Connected to Redis at {self.redis_url}")
        return self._client
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((redis.ConnectionError, redis.TimeoutError)),
        before=before_log(logger, logging.DEBUG)
    )
    async def execute_with_retry(self, operation, *args, **kwargs) -> Any:
        """
        Execute Redis operation with retry logic
        
        Args:
            operation: Async Redis operation to execute
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Operation result
        """
        client = await self._get_client()
        # If operation is a method name string, get the actual method
        if isinstance(operation, str):
            operation = getattr(client, operation)
            return await operation(*args, **kwargs)
        # If operation is a callable that needs client
        return await operation(client, *args, **kwargs)
    
    async def is_connected(self) -> bool:
        """
        Check if Redis connection is active
        
        Returns:
            True if connected, False otherwise
        """
        try:
            client = await self._get_client()
            await client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis connection check failed: {e}")
            return False
    
    async def reconnect(self) -> bool:
        """
        Force reconnection to Redis
        
        Returns:
            True if reconnection successful
        """
        try:
            await self.close()
            await self._get_client()
            return True
        except Exception as e:
            logger.error(f"Failed to reconnect to Redis: {e}")
            return False
    
    async def close(self):
        """Close Redis connections"""
        try:
            if self._client:
                await self._client.close()
                self._client = None
            if self._pool:
                await self._pool.disconnect()
                self._pool = None
            logger.debug("Redis connections closed")
        except Exception as e:
            logger.error(f"Error closing Redis connections: {e}")