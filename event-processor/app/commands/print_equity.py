"""
Print equity command implementation.
"""

from typing import Dict, Any
from app.commands.base import EventCommand, EventCommandResult, CommandStatus
from app.logger import setup_logger, log_with_event

logger = setup_logger(__name__)


class PrintEquityCommand(EventCommand):
    """Command to print account equity"""
    
    def _get_command_type(self) -> str:
        return "print-equity"
    
    async def execute(self, services: Dict[str, Any]) -> EventCommandResult:
        """Execute print equity command"""
        log_with_event(logger, 'info',
                      f"Printing equity for account {self.account_id}",
                      event_id=self.event_id, account_id=self.account_id)
        
        try:
            ibkr_client = services.get('ibkr_client')
            if not ibkr_client:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="IBKR client not available"
                )
            
            account_value = await ibkr_client.get_account_value(self.account_id)
            
            log_with_event(logger, 'info',
                          f"Total account value for {self.account_id}: ${account_value:.2f}",
                          event_id=self.event_id, account_id=self.account_id,
                          account_value=account_value)
            
            return EventCommandResult(
                status=CommandStatus.SUCCESS,
                message="Print equity command executed successfully",
                data={"action": "print-equity", "account_value": account_value}
            )
            
        except Exception as e:
            logger.error(f"Print equity failed: {e}", extra={
                'event_id': self.event_id,
                'account_id': self.account_id,
                'error': str(e)
            })
            
            return EventCommandResult(
                status=CommandStatus.FAILED,
                error=str(e)
            )