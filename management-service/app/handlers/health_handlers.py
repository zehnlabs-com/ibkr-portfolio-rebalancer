"""
Health check API handlers
"""
import logging

from app.services.interfaces import IHealthService
from app.models.health_models import DetailedHealthStatus

logger = logging.getLogger(__name__)


class HealthHandlers:
    """Health API handlers"""
    
    def __init__(self, health_service: IHealthService):
        self.health_service = health_service
    
    async def detailed_health_check(self) -> DetailedHealthStatus:
        """Detailed health check"""
        try:
            result = await self.health_service.get_detailed_health()
            return DetailedHealthStatus(**result)
        except Exception as e:
            logger.error(f"Detailed health check failed: {e}")
            return DetailedHealthStatus(
                status="error",
                healthy=False,
                queue_length=0,
                active_events_count=0,
                retry_events_count=0,
                delayed_events_count=0,
                message=f"Detailed health check failed: {str(e)}"
            )