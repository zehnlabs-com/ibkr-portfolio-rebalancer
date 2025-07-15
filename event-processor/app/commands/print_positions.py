"""
Print positions command implementation.
"""

from typing import Dict, Any
from app.commands.base import EventCommand, EventCommandResult, CommandStatus
from app.logger import EventLogger

event_logger = EventLogger(__name__)


class PrintPositionsCommand(EventCommand):
    """Command to print account positions"""
    
    def _get_command_type(self) -> str:
        return "print-positions"
    
    async def execute(self, services: Dict[str, Any]) -> EventCommandResult:
        """Execute print positions command"""
        event_logger.log_info(f"Printing positions for account {self.event.account_id}", self.event)
        
        try:
            ibkr_client = services.get('ibkr_client')
            if not ibkr_client:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="IBKR client not available"
                )
            
            positions = await ibkr_client.get_positions(self.event.account_id)
            
            if not positions:
                event_logger.log_info(f"No positions found for account {self.event.account_id}", self.event)
            else:
                event_logger.log_info(f"Current positions for account {self.event.account_id}:", self.event)
                
                for position in positions:
                    event_logger.log_info(f"  {position['symbol']}: {position['position']} shares, market value: ${position['market_value']:.2f}, avg cost: ${position['avg_cost']:.2f}", self.event)
            
            return EventCommandResult(
                status=CommandStatus.SUCCESS,
                message="Print positions command executed successfully",
                data={"action": "print-positions", "positions": positions}
            )
            
        except Exception as e:
            event_logger.log_error(f"Print positions failed: {e}", self.event)
            
            return EventCommandResult(
                status=CommandStatus.FAILED,
                error=str(e)
            )