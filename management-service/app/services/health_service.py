"""
Health service implementation
"""
import logging
from typing import Dict, Any, List

from app.services.interfaces import IHealthService
from app.repositories.interfaces import IHealthRepository, IQueueRepository

logger = logging.getLogger(__name__)


class HealthService(IHealthService):
    """Health service implementation"""
    
    def __init__(self, health_repository: IHealthRepository, queue_repository: IQueueRepository):
        self.health_repository = health_repository
        self.queue_repository = queue_repository
    
    async def check_health(self) -> Dict[str, Any]:
        """Check system health based on events with times_queued > 1 and delayed events"""
        try:
            events_with_retries = await self.health_repository.count_events_with_retries()
            delayed_events_count = await self.queue_repository.get_delayed_events_count()
            
            total_failing_events = events_with_retries + delayed_events_count
            
            if total_failing_events == 0:
                return {
                    "status": "healthy",
                    "healthy": True,
                    "events_with_retries": 0,
                    "delayed_events": 0,
                    "message": "No events require retry"
                }
            else:
                return {
                    "status": "unhealthy",
                    "healthy": False,
                    "events_with_retries": events_with_retries,
                    "delayed_events": delayed_events_count,
                    "message": f"{total_failing_events} events have failed ({events_with_retries} in queue with retries, {delayed_events_count} delayed)"
                }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "healthy": False,
                "events_with_retries": 0,
                "delayed_events": 0,
                "message": f"Health check failed: {str(e)}"
            }
    
    async def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health information including retry statistics"""
        try:
            # Get queue metrics
            queue_length = await self.queue_repository.get_queue_length()
            active_events_count = await self.queue_repository.get_active_events_count()
            delayed_events_count = await self.queue_repository.get_delayed_events_count()
            
            # Get events and analyze them
            events = await self.queue_repository.get_queue_events(limit=1000)  # Get more for analysis
            
            total_events = len(events)
            events_with_retries = 0
            max_retries = 0
            retry_distribution = {}
            
            for event in events:
                times_queued = event.get("times_queued", 1)
                
                if times_queued > 1:
                    events_with_retries += 1
                    max_retries = max(max_retries, times_queued)
                
                # Count retry distribution
                retry_distribution[str(times_queued)] = retry_distribution.get(str(times_queued), 0) + 1
            
            total_failing_events = events_with_retries + delayed_events_count
            healthy = total_failing_events == 0
            
            return {
                "status": "healthy" if healthy else "unhealthy",
                "healthy": healthy,
                "queue_length": queue_length,
                "active_events_count": active_events_count,
                "delayed_events_count": delayed_events_count,
                "total_events": total_events,
                "events_with_retries": events_with_retries,
                "max_retry_count": max_retries,
                "retry_distribution": retry_distribution,
                "message": f"System {'healthy' if healthy else 'has issues'}: {events_with_retries} active events with retries, {delayed_events_count} delayed events"
            }
        except Exception as e:
            logger.error(f"Detailed health check failed: {e}")
            return {
                "status": "error",
                "healthy": False,
                "message": f"Detailed health check failed: {str(e)}"
            }
    
    async def get_problematic_events(self, min_retries: int = 2) -> List[Dict[str, Any]]:
        """Get problematic events"""
        try:
            return await self.health_repository.get_problematic_events(min_retries)
        except Exception as e:
            logger.error(f"Failed to get problematic events: {e}")
            return []