"""
Rebalance command implementation.
"""

from typing import Dict, Any
from app.commands.base import EventCommand, EventCommandResult, CommandStatus
from app.logger import AppLogger
from app.models.account_config import EventAccountConfig
from app.services.rebalancer_service import TradingHoursException
from app.config import config

app_logger = AppLogger(__name__)


class RebalanceCommand(EventCommand):
    """Command to execute portfolio rebalancing"""
    
    def _get_command_type(self) -> str:
        return "rebalance"
    
    async def execute(self, services: Dict[str, Any]) -> EventCommandResult:
        """Execute rebalance command with trading hours validation"""
        
        try:
            rebalancer_service = services.get('rebalancer_service')
            queue_service = services.get('queue_service')
            
            if not rebalancer_service:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="Rebalancer service not available"
                )
            
            if not queue_service:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="Queue service not available"
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
            
        except TradingHoursException as e:
            # Handle trading hours validation failure
            app_logger.log_info(f"Rebalance delayed due to trading hours: {e.message}", self.event)
            
            if e.next_start_time:
                # Add event to delayed execution queue
                await queue_service.add_to_delayed_queue(self.event, e.next_start_time)
                
                return EventCommandResult(
                    status=CommandStatus.SUCCESS,
                    message=f"Rebalance delayed until next trading window: {e.next_start_time.strftime('%Y-%m-%d %H:%M:%S')}",
                    data={"action": "delayed", "next_execution_time": e.next_start_time.isoformat(), "symbol_status": e.symbol_status}
                )
            else:
                # No next start time available - treat as failure
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error=f"Trading hours validation failed and no next trading window available: {e.message}"
                )
            
        except Exception as e:
            app_logger.log_error(f"Rebalance failed: {e}", self.event)
            
            return EventCommandResult(
                status=CommandStatus.FAILED,
                error=str(e)
            )