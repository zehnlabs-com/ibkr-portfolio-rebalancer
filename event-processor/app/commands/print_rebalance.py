"""
Print rebalance command implementation.
"""

from typing import Dict, Any
from app.commands.base import EventCommand, EventCommandResult, CommandStatus
from app.logger import AppLogger
from app.models.account_config import EventAccountConfig

app_logger = AppLogger(__name__)


class PrintRebalanceCommand(EventCommand):
    """Command to print rebalance information"""
    
    def _get_command_type(self) -> str:
        return "print-rebalance"
    
    async def execute(self, services: Dict[str, Any]) -> EventCommandResult:
        """Execute print rebalance command"""
        app_logger.log_info(f"Printing rebalance orders for account {self.event.account_id} (dry run)", self.event)
        
        try:
            rebalancer_service = services.get('rebalancer_service')
            if not rebalancer_service:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="Rebalancer service not available"
                )
            
            # Get account configuration from event payload
            account_config_data = self.event.payload.get('account_config')
            
            if not account_config_data:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error=f"No account configuration found in event payload for account {self.event.account_id}"
                )
            
            # Create account config object from the event payload
            account_config = EventAccountConfig(account_config_data)
            
            # Execute dry run rebalancing
            result = await rebalancer_service.dry_run_rebalance(account_config)
            
            if not result.orders:
                app_logger.log_info(f"No rebalance orders needed for account {self.event.account_id}", self.event)
            else:
                app_logger.log_info(f"Rebalance orders for account {self.event.account_id} (would execute {len(result.orders)} orders):", self.event)
                
                for order in result.orders:
                    app_logger.log_info(f"  Would {order.action} {order.quantity} shares of {order.symbol} (${order.market_value:.2f})", self.event)
            
            return EventCommandResult(
                status=CommandStatus.SUCCESS,
                message="Print rebalance command executed successfully",
                data={"action": "print-rebalance", "orders": result.orders, "equity_info": result.equity_info}
            )
            
        except Exception as e:
            app_logger.log_error(f"Print rebalance failed: {e}", self.event)
            
            return EventCommandResult(
                status=CommandStatus.FAILED,
                error=str(e)
            )