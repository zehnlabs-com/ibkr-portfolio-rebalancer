"""
Rebalance command implementation.
"""

from typing import Dict, Any
from app.commands.base import EventCommand, EventCommandResult, CommandStatus
from app.logger import setup_logger, log_with_event
from app.models.account_config import EventAccountConfig

logger = setup_logger(__name__)


class RebalanceCommand(EventCommand):
    """Command to execute portfolio rebalancing"""
    
    def _get_command_type(self) -> str:
        return "rebalance"
    
    async def execute(self, services: Dict[str, Any]) -> EventCommandResult:
        """Execute rebalance command - MUST BE 100% SAME AS OLD CODE"""
        
        try:
            rebalancer_service = services.get('rebalancer_service')
            market_hours_service = services.get('market_hours_service')
            
            if not rebalancer_service:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="Rebalancer service not available"
                )
            
            if not market_hours_service:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="Market hours service not available"
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
            
            # EXACT COPY FROM OLD IMPLEMENTATION - Check if markets are open for rebalance operations
            if not await market_hours_service.is_market_open():
                error_msg = "Markets are closed - rebalance operations not allowed"
                log_with_event(logger, 'error', error_msg, 
                              event_id=self.event_id, account_id=self.account_id)
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error=error_msg
                )
            
            # EXACT COPY FROM OLD IMPLEMENTATION - Determine order type based on market timing
            order_type = await market_hours_service.get_order_type()
            
            log_with_event(logger, 'info',
                          f"Using order type: {order_type}",
                          event_id=self.event_id, account_id=self.account_id)
            
            # EXACT COPY FROM OLD IMPLEMENTATION - Execute rebalancing
            result = await rebalancer_service.rebalance_account(
                account_config, 
                order_type
            )
            
            log_with_event(logger, 'info',
                          f"Rebalance completed - orders: {len(result.orders)}",
                          event_id=self.event_id, account_id=self.account_id,
                          orders_placed=len(result.orders))
            
            return EventCommandResult(
                status=CommandStatus.SUCCESS,
                message="Rebalance command executed successfully",
                data={"action": "rebalance", "result": result}
            )
            
        except Exception as e:
            logger.error(f"Rebalance failed: {e}", extra={
                'event_id': self.event_id,
                'account_id': self.account_id,
                'error': str(e)
            })
            
            return EventCommandResult(
                status=CommandStatus.FAILED,
                error=str(e)
            )