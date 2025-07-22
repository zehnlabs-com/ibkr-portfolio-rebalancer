"""
Cancel orders command implementation.
"""

from typing import Dict, Any
from app.commands.base import EventCommand, EventCommandResult, CommandStatus
from app.logger import AppLogger

app_logger = AppLogger(__name__)


class CancelOrdersCommand(EventCommand):
    """Command to cancel account orders"""
    
    def _get_command_type(self) -> str:
        return "cancel-orders"
    
    async def execute(self, services: Dict[str, Any]) -> EventCommandResult:
        """Execute cancel orders command"""
        app_logger.log_info(f"Cancelling all pending orders for account {self.event.account_id}", self.event)
        
        try:
            ibkr_client = services.get('ibkr_client')
            if not ibkr_client:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="IBKR client not available"
                )
            
            cancelled_orders = await ibkr_client.cancel_all_orders(self.event.account_id)
            
            if not cancelled_orders:
                app_logger.log_info(f"No pending orders found for account {self.event.account_id}", self.event)
            else:
                app_logger.log_info(f"Cancelled {len(cancelled_orders)} orders for account {self.event.account_id}", self.event)
            
            return EventCommandResult(
                status=CommandStatus.SUCCESS,
                message="Cancel orders command executed successfully",
                data={"action": "cancel-orders", "cancelled_orders": cancelled_orders}
            )
            
        except Exception as e:
            app_logger.log_error(f"Cancel orders failed: {e}", self.event)
            
            return EventCommandResult(
                status=CommandStatus.FAILED,
                error=str(e)
            )