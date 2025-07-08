"""
Health check command implementation.
"""

from typing import Dict, Any
from app.commands.base import EventCommand, EventCommandResult, CommandStatus
from app.logger import setup_logger, log_with_event

logger = setup_logger(__name__)


class HealthCheckCommand(EventCommand):
    """Command to perform health check"""
    
    def _get_command_type(self) -> str:
        return "health"
    
    async def execute(self, services: Dict[str, Any]) -> EventCommandResult:
        """Execute health check command"""
        log_with_event(logger, 'info',
                      f"Checking health status for account {self.account_id}",
                      event_id=self.event_id, account_id=self.account_id)
        
        try:
            ibkr_client = services.get('ibkr_client')
            event_service = services.get('event_service')
            
            if not ibkr_client:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="IBKR client not available"
                )
            
            if not event_service:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="Event service not available"
                )
            
            # Check IBKR connection
            ibkr_connected = await ibkr_client.ensure_connected()
            
            # Check database connection
            db_connected = await event_service.is_connected()
            
            # Get some basic metrics
            try:
                account_value = await ibkr_client.get_account_value(self.account_id)
                account_accessible = True
            except Exception as e:
                account_value = None
                account_accessible = False
                log_with_event(logger, 'warning',
                              f"Cannot access account {self.account_id}: {e}",
                              event_id=self.event_id, account_id=self.account_id)
            
            health_status = {
                "ibkr_connected": ibkr_connected,
                "database_connected": db_connected,
                "account_accessible": account_accessible,
                "account_value": account_value
            }
            
            log_with_event(logger, 'info',
                          f"Health status for account {self.account_id}: "
                          f"IBKR connected: {ibkr_connected}, "
                          f"DB connected: {db_connected}, "
                          f"Account accessible: {account_accessible}, "
                          f"Account value: ${account_value:.2f}" if account_value else "Account value: N/A",
                          event_id=self.event_id, account_id=self.account_id,
                          **health_status)
            
            return EventCommandResult(
                status=CommandStatus.SUCCESS,
                message="Health check completed successfully",
                data={"action": "health", "status": health_status}
            )
                
        except Exception as e:
            logger.error(f"Health check failed: {e}", extra={
                'event_id': self.event_id,
                'account_id': self.account_id,
                'error': str(e)
            })
            
            return EventCommandResult(
                status=CommandStatus.FAILED,
                error=str(e)
            )