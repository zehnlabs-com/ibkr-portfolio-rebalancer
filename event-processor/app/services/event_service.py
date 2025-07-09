"""
PostgreSQL Event Service for Event Processor
"""
import json
from typing import Dict, Any, Optional
from datetime import datetime, date, timezone
from app.database import db_manager
from app.logger import setup_logger

logger = setup_logger(__name__)


class EventService:
    """PostgreSQL service for event tracking and audit"""
    
    def __init__(self):
        self.db = db_manager
        
    async def update_status(self, event_id: str, status: str, error_message: str = None) -> None:
        """Update event status with optional error message"""
        try:
            if status == 'processing':
                await self.db.execute_command(
                    """
                    UPDATE rebalance_events 
                    SET status = $1, started_at = $2 
                    WHERE event_id = $3
                    """,
                    status,
                    datetime.now(timezone.utc),
                    event_id
                )
            elif status in ['completed', 'failed']:
                await self.db.execute_command(
                    """
                    UPDATE rebalance_events 
                    SET status = $1, completed_at = $2, error_message = $3 
                    WHERE event_id = $4
                    """,
                    status,
                    datetime.now(timezone.utc),
                    error_message,
                    event_id
                )
            else:
                await self.db.execute_command(
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
    
    async def increment_retry(self, event_id: str) -> int:
        """
        Increment retry count and set first_failed_date if not set
        
        Returns:
            int: Current retry count
        """
        try:
            # Get current retry count and first_failed_date
            result = await self.db.execute_query(
                """
                SELECT retry_count, first_failed_date 
                FROM rebalance_events 
                WHERE event_id = $1
                """,
                event_id
            )
            
            if not result:
                raise ValueError(f"Event {event_id} not found")
            
            current_retry_count = result[0]['retry_count'] or 0
            first_failed_date = result[0]['first_failed_date']
            
            new_retry_count = current_retry_count + 1
            
            # Set first_failed_date if not already set
            if first_failed_date is None:
                first_failed_date = date.today()
                await self.db.execute_command(
                    """
                    UPDATE rebalance_events 
                    SET retry_count = $1, first_failed_date = $2 
                    WHERE event_id = $3
                    """,
                    new_retry_count,
                    first_failed_date,
                    event_id
                )
            else:
                await self.db.execute_command(
                    """
                    UPDATE rebalance_events 
                    SET retry_count = $1 
                    WHERE event_id = $2
                    """,
                    new_retry_count,
                    event_id
                )
            
            logger.info(f"Event retry count incremented", extra={
                'event_id': event_id,
                'retry_count': new_retry_count
            })
            
            return new_retry_count
            
        except Exception as e:
            logger.error(f"Failed to increment retry count for event {event_id}: {e}")
            raise

    async def update_times_queued(self, event_id: str, times_queued: int) -> None:
        """
        Update times_queued field for an event
        
        Args:
            event_id: Event ID
            times_queued: New times_queued value
        """
        try:
            await self.db.execute_command(
                """
                UPDATE rebalance_events 
                SET times_queued = $1 
                WHERE event_id = $2
                """,
                times_queued,
                event_id
            )
            
            logger.info(f"Event times_queued updated", extra={
                'event_id': event_id,
                'times_queued': times_queued
            })
            
        except Exception as e:
            logger.error(f"Failed to update times_queued for event {event_id}: {e}")
            raise
    
    async def should_retry(self, event_id: str, max_retry_days: int) -> bool:
        """
        Check if event should be retried based on day limit
        
        Returns:
            bool: True if should retry, False if exceeded limit
        """
        try:
            result = await self.db.execute_query(
                """
                SELECT first_failed_date 
                FROM rebalance_events 
                WHERE event_id = $1
                """,
                event_id
            )
            
            if not result or not result[0]['first_failed_date']:
                # No first_failed_date means this is first failure, should retry
                return True
            
            first_failed_date = result[0]['first_failed_date']
            days_since_first_failure = (date.today() - first_failed_date).days
            
            should_retry = days_since_first_failure < max_retry_days
            
            logger.debug(f"Retry check for event", extra={
                'event_id': event_id,
                'days_since_first_failure': days_since_first_failure,
                'max_retry_days': max_retry_days,
                'should_retry': should_retry
            })
            
            return should_retry
            
        except Exception as e:
            logger.error(f"Failed to check retry status for event {event_id}: {e}")
            return False
    
    async def get_event_stats(self) -> Dict[str, Any]:
        """Get event statistics"""
        try:
            # Get counts by status for last 24 hours
            status_result = await self.db.execute_query(
                """
                SELECT 
                    status,
                    COUNT(*) as count
                FROM rebalance_events 
                WHERE received_at >= NOW() - INTERVAL '24 hours'
                GROUP BY status
                """
            )
            
            # Get events with high queue counts
            retry_result = await self.db.execute_query(
                """
                SELECT 
                    COUNT(*) as count
                FROM rebalance_events 
                WHERE times_queued > 1
                """
            )
            
            stats = {row['status']: row['count'] for row in status_result}
            stats['events_with_retries'] = retry_result[0]['count'] if retry_result else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get event stats: {e}")
            return {}
    
    async def is_connected(self) -> bool:
        """Check if PostgreSQL connection is active"""
        return await self.db.is_connected()