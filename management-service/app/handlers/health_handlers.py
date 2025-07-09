"""
Health check API handlers
"""
import logging
from fastapi import HTTPException, status

from app.services.interfaces import IHealthService
from app.models.health_models import HealthStatus, DetailedHealthStatus

logger = logging.getLogger(__name__)


class HealthHandlers:
    """Health API handlers"""
    
    def __init__(self, health_service: IHealthService):
        self.health_service = health_service
    
    async def health_check(self) -> HealthStatus:
        """Basic health check"""
        try:
            result = await self.health_service.check_health()
            return HealthStatus(**result)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthStatus(
                status="error",
                healthy=False,
                events_with_retries=0,
                message=f"Health check failed: {str(e)}"
            )
    
    async def detailed_health_check(self) -> DetailedHealthStatus:
        """Detailed health check"""
        try:
            result = await self.health_service.get_detailed_health()
            return DetailedHealthStatus(**result)
        except Exception as e:
            logger.error(f"Detailed health check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Detailed health check failed: {str(e)}"
            )