"""
Rebalance command implementation.
"""

from typing import Dict, Any
from app.commands.base import EventCommand, EventCommandResult, CommandStatus
from app.logger import AppLogger
from app.models.account_config import EventAccountConfig
from app.config import config

app_logger = AppLogger(__name__)


class RebalanceCommand(EventCommand):
    """Command to execute portfolio rebalancing"""
    
    def _get_command_type(self) -> str:
        return "rebalance"
    
    async def execute(self, services: Dict[str, Any]) -> EventCommandResult:
        """Execute rebalance command - MUST BE 100% SAME AS OLD CODE"""
        
        try:
            rebalancer_service = services.get('rebalancer_service')
            
            if not rebalancer_service:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="Rebalancer service not available"
                )
            
            if not self.event.payload.get('strategy_name'):
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error=f"No strategy_name found in event payload for account {self.event.account_id}"
                )
            
            account_config = EventAccountConfig(self.event.payload)
            
            app_logger.log_info("Using MKT order type (only type supported)", self.event)
            
            # Execute rebalancing (always uses MKT orders)
            result = await rebalancer_service.rebalance_account(account_config, self.event)
            
            app_logger.log_info(f"Rebalance completed - orders: {len(result.orders)}", self.event)
            
            return EventCommandResult(
                status=CommandStatus.SUCCESS,
                message="Rebalance command executed successfully",
                data={"action": "rebalance", "result": result}
            )
            
        except Exception as e:
            app_logger.log_error(f"Rebalance failed: {e}", self.event)
            
            return EventCommandResult(
                status=CommandStatus.FAILED,
                error=str(e)
            )