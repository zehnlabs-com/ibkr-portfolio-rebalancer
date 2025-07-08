"""
Print rebalance command implementation.
"""

from typing import Dict, Any
from app.commands.base import EventCommand, EventCommandResult, CommandStatus
from app.logger import setup_logger, log_with_event
from app.models.account_config import EventAccountConfig

logger = setup_logger(__name__)


class PrintRebalanceCommand(EventCommand):
    """Command to print rebalance information"""
    
    def _get_command_type(self) -> str:
        return "print-rebalance"
    
    async def execute(self, services: Dict[str, Any]) -> EventCommandResult:
        """Execute print rebalance command"""
        log_with_event(logger, 'info',
                      f"Printing rebalance orders for account {self.account_id} (dry run)",
                      event_id=self.event_id, account_id=self.account_id)
        
        try:
            rebalancer_service = services.get('rebalancer_service')
            if not rebalancer_service:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="Rebalancer service not available"
                )
            
            # Get account configuration from event payload
            account_config_data = self.event_data.get('data', {}).get('account_config') or \
                                self.event_data.get('payload', {}).get('account_config')
            
            if not account_config_data:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error=f"No account configuration found in event payload for account {self.account_id}"
                )
            
            # Create account config object from the event payload
            account_config = EventAccountConfig(account_config_data)
            
            # Execute dry run rebalancing
            result = await rebalancer_service.dry_run_rebalance(account_config)
            
            if not result.orders:
                log_with_event(logger, 'info',
                              f"No rebalance orders needed for account {self.account_id}",
                              event_id=self.event_id, account_id=self.account_id)
            else:
                log_with_event(logger, 'info',
                              f"Rebalance orders for account {self.account_id} (would execute {len(result.orders)} orders):",
                              event_id=self.event_id, account_id=self.account_id,
                              orders_count=len(result.orders))
                
                for order in result.orders:
                    log_with_event(logger, 'info',
                                  f"  Would {order.action} {order.quantity} shares of {order.symbol} "
                                  f"(${order.market_value:.2f})",
                                  event_id=self.event_id, account_id=self.account_id,
                                  action=order.action, quantity=order.quantity,
                                  symbol=order.symbol, market_value=order.market_value)
            
            return EventCommandResult(
                status=CommandStatus.SUCCESS,
                message="Print rebalance command executed successfully",
                data={"action": "print-rebalance", "orders": result.orders, "equity_info": result.equity_info}
            )
            
        except Exception as e:
            logger.error(f"Print rebalance failed: {e}", extra={
                'event_id': self.event_id,
                'account_id': self.account_id,
                'error': str(e)
            })
            
            return EventCommandResult(
                status=CommandStatus.FAILED,
                error=str(e)
            )