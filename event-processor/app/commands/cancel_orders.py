"""
Cancel orders command implementation.
"""

from typing import Dict, Any
from app.commands.base import EventCommand, EventCommandResult, CommandStatus
from app.logger import setup_logger, log_with_event

logger = setup_logger(__name__)


class CancelOrdersCommand(EventCommand):
    """Command to cancel account orders"""
    
    def _get_command_type(self) -> str:
        return "cancel-orders"
    
    async def execute(self, services: Dict[str, Any]) -> EventCommandResult:
        """Execute cancel orders command"""
        log_with_event(logger, 'info',
                      f"Cancelling all pending orders for account {self.account_id}",
                      event_id=self.event_id, account_id=self.account_id)
        
        try:
            ibkr_client = services.get('ibkr_client')
            if not ibkr_client:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="IBKR client not available"
                )
            
            cancelled_orders = await ibkr_client.cancel_all_orders(self.account_id)
            
            if not cancelled_orders:
                log_with_event(logger, 'info',
                              f"No pending orders found for account {self.account_id}",
                              event_id=self.event_id, account_id=self.account_id)
            else:
                log_with_event(logger, 'info',
                              f"Cancelled {len(cancelled_orders)} orders for account {self.account_id}",
                              event_id=self.event_id, account_id=self.account_id,
                              cancelled_orders_count=len(cancelled_orders))
            
            return EventCommandResult(
                status=CommandStatus.SUCCESS,
                message="Cancel orders command executed successfully",
                data={"action": "cancel-orders", "cancelled_orders": cancelled_orders}
            )
            
        except Exception as e:
            logger.error(f"Cancel orders failed: {e}", extra={
                'event_id': self.event_id,
                'account_id': self.account_id,
                'error': str(e)
            })
            
            return EventCommandResult(
                status=CommandStatus.FAILED,
                error=str(e)
            )