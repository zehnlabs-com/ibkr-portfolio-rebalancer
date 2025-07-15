"""
Print equity command implementation.
"""

from typing import Dict, Any
from app.commands.base import EventCommand, EventCommandResult, CommandStatus
from app.logger import EventLogger

event_logger = EventLogger(__name__)


class PrintEquityCommand(EventCommand):
    """Command to print account equity"""
    
    def _get_command_type(self) -> str:
        return "print-equity"
    
    async def execute(self, services: Dict[str, Any]) -> EventCommandResult:
        """Execute print equity command"""
        event_logger.log_info(f"Printing equity for account {self.event.account_id}", self.event)
        
        try:
            ibkr_client = services.get('ibkr_client')
            if not ibkr_client:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="IBKR client not available"
                )
            
            account_value = await ibkr_client.get_account_value(self.event.account_id)
            
            event_logger.log_info(f"Total account value for {self.event.account_id}: ${account_value:.2f}", self.event)
            
            return EventCommandResult(
                status=CommandStatus.SUCCESS,
                message="Print equity command executed successfully",
                data={"action": "print-equity", "account_value": account_value}
            )
            
        except Exception as e:
            event_logger.log_error(f"Print equity failed: {e}", self.event)
            
            return EventCommandResult(
                status=CommandStatus.FAILED,
                error=str(e)
            )