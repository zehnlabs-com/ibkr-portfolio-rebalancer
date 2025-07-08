"""
Print positions command implementation.
"""

from typing import Dict, Any
from app.commands.base import EventCommand, EventCommandResult, CommandStatus
from app.logger import setup_logger, log_with_event

logger = setup_logger(__name__)


class PrintPositionsCommand(EventCommand):
    """Command to print account positions"""
    
    def _get_command_type(self) -> str:
        return "print-positions"
    
    async def execute(self, services: Dict[str, Any]) -> EventCommandResult:
        """Execute print positions command"""
        log_with_event(logger, 'info',
                      f"Printing positions for account {self.account_id}",
                      event_id=self.event_id, account_id=self.account_id)
        
        try:
            ibkr_client = services.get('ibkr_client')
            if not ibkr_client:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="IBKR client not available"
                )
            
            positions = await ibkr_client.get_positions(self.account_id)
            
            if not positions:
                log_with_event(logger, 'info',
                              f"No positions found for account {self.account_id}",
                              event_id=self.event_id, account_id=self.account_id)
            else:
                log_with_event(logger, 'info',
                              f"Current positions for account {self.account_id}:",
                              event_id=self.event_id, account_id=self.account_id)
                
                for position in positions:
                    log_with_event(logger, 'info',
                                  f"  {position['symbol']}: {position['position']} shares, "
                                  f"market value: ${position['market_value']:.2f}, "
                                  f"avg cost: ${position['avg_cost']:.2f}",
                                  event_id=self.event_id, account_id=self.account_id,
                                  symbol=position['symbol'], position=position['position'],
                                  market_value=position['market_value'], avg_cost=position['avg_cost'])
            
            return EventCommandResult(
                status=CommandStatus.SUCCESS,
                message="Print positions command executed successfully",
                data={"action": "print-positions", "positions": positions}
            )
            
        except Exception as e:
            logger.error(f"Print positions failed: {e}", extra={
                'event_id': self.event_id,
                'account_id': self.account_id,
                'error': str(e)
            })
            
            return EventCommandResult(
                status=CommandStatus.FAILED,
                error=str(e)
            )