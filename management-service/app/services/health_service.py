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
        """Check system health based on retry events"""
        try:
            retry_events_count = await self.queue_repository.get_retry_events_count()
            
            if retry_events_count == 0:
                return {
                    "status": "healthy",
                    "healthy": True,
                    "retry_events_count": 0,
                    "message": "No events require retry"
                }
            else:
                return {
                    "status": "unhealthy",
                    "healthy": False,
                    "retry_events_count": retry_events_count,
                    "message": f"{retry_events_count} events in retry queue"
                }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "healthy": False,
                "retry_events_count": 0,
                "message": f"Health check failed: {str(e)}"
            }
    
    async def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health information"""
        try:
            # Get queue metrics
            queue_length = await self.queue_repository.get_queue_length()
            active_events_count = await self.queue_repository.get_active_events_count()
            retry_events_count = await self.queue_repository.get_retry_events_count()
            delayed_events_count = await self.queue_repository.get_delayed_events_count()
            
            healthy = retry_events_count == 0
            
            return {
                "status": "healthy" if healthy else "unhealthy",
                "healthy": healthy,
                "queue_length": queue_length,
                "active_events_count": active_events_count,
                "retry_events_count": retry_events_count,
                "delayed_events_count": delayed_events_count,
                "message": f"System {'healthy' if healthy else 'has issues'}: {retry_events_count} retry events, {delayed_events_count} delayed events"
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