"""
PostgreSQL database connection management for Event Processor
"""
import asyncio
import asyncpg
from typing import Optional
from app.config import config
from app.logger import setup_logger

logger = setup_logger(__name__)


class DatabaseManager:
    """Database connection manager for PostgreSQL"""
    
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
    
    async def init_connection_pool(self):
        """Initialize PostgreSQL connection pool"""
        try:
            self._pool = await asyncpg.create_pool(
                host=config.postgresql.host,
                port=config.postgresql.port,
                database=config.postgresql.database,
                user=config.postgresql.username,
                password=config.postgresql.password,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("PostgreSQL connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection pool: {e}")
            raise
    
    async def close_connection_pool(self):
        """Close PostgreSQL connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("PostgreSQL connection pool closed")
    
    async def get_connection(self):
        """Get a database connection from the pool"""
        if not self._pool:
            await self.init_connection_pool()
        return self._pool.acquire()
    
    async def execute_query(self, query: str, *args):
        """Execute a query and return results"""
        if not self._pool:
            await self.init_connection_pool()
            
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def execute_command(self, command: str, *args):
        """Execute a command (INSERT, UPDATE, DELETE)"""
        if not self._pool:
            await self.init_connection_pool()
            
        async with self._pool.acquire() as conn:
            return await conn.execute(command, *args)
    
    async def is_connected(self) -> bool:
        """Check if database connection is active"""
        if not self._pool:
            return False
            
        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False

# Global database manager instance
db_manager = DatabaseManager()