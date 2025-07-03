"""
PostgreSQL Event Service for Event Broker
"""
import asyncio
import asyncpg
import json
from typing import Dict, Any, Optional
from datetime import datetime
from app.config import config
from app.logger import setup_logger

logger = setup_logger(__name__, level=config.LOG_LEVEL)


class EventService:
    """PostgreSQL service for event tracking and audit"""
    
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
                min_size=1,
                max_size=5
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
    
    async def create_event(self, event_id: str, account_id: str, payload: Dict[str, Any]) -> None:
        """Create new event record"""
        if not self._pool:
            await self.init_connection_pool()
            
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO rebalance_events 
                    (event_id, account_id, status, payload, received_at) 
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    event_id,
                    account_id,
                    'pending',
                    json.dumps(payload),
                    datetime.utcnow()
                )
                
            logger.info(f"Event created in database", extra={
                'event_id': event_id,
                'account_id': account_id
            })
            
        except Exception as e:
            logger.error(f"Failed to create event {event_id}: {e}")
            raise
    
    async def update_event_status(self, event_id: str, status: str, error_message: str = None) -> None:
        """Update event status"""
        if not self._pool:
            await self.init_connection_pool()
            
        try:
            async with self._pool.acquire() as conn:
                if status == 'processing':
                    await conn.execute(
                        """
                        UPDATE rebalance_events 
                        SET status = $1, started_at = $2 
                        WHERE event_id = $3
                        """,
                        status,
                        datetime.utcnow(),
                        event_id
                    )
                elif status in ['completed', 'failed']:
                    await conn.execute(
                        """
                        UPDATE rebalance_events 
                        SET status = $1, completed_at = $2, error_message = $3 
                        WHERE event_id = $4
                        """,
                        status,
                        datetime.utcnow(),
                        error_message,
                        event_id
                    )
                else:
                    await conn.execute(
                        """
                        UPDATE rebalance_events 
                        SET status = $1, error_message = $2 
                        WHERE event_id = $3
                        """,
                        status,
                        error_message,
                        event_id
                    )
                    
            logger.info(f"Event status updated", extra={
                'event_id': event_id,
                'status': status
            })
            
        except Exception as e:
            logger.error(f"Failed to update event {event_id} status: {e}")
            raise
    
    async def get_event_stats(self) -> Dict[str, Any]:
        """Get event statistics"""
        if not self._pool:
            await self.init_connection_pool()
            
        try:
            async with self._pool.acquire() as conn:
                # Get counts by status for last 24 hours
                result = await conn.fetch(
                    """
                    SELECT 
                        status,
                        COUNT(*) as count
                    FROM rebalance_events 
                    WHERE received_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY status
                    """
                )
                
                stats = {row['status']: row['count'] for row in result}
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get event stats: {e}")
            return {}
    
    async def is_connected(self) -> bool:
        """Check if PostgreSQL connection is active"""
        if not self._pool:
            return False
            
        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False