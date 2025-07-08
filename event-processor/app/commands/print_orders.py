"""
Print orders command implementation.
"""

from typing import Dict, Any
from app.commands.base import EventCommand, EventCommandResult, CommandStatus
from app.logger import setup_logger, log_with_event

logger = setup_logger(__name__)


class PrintOrdersCommand(EventCommand):
    """Command to print account orders"""
    
    def _get_command_type(self) -> str:
        return "print-orders"
    
    async def execute(self, services: Dict[str, Any]) -> EventCommandResult:
        """Execute print orders command"""
        log_with_event(logger, 'info',
                      f"Printing pending orders for account {self.account_id}",
                      event_id=self.event_id, account_id=self.account_id)
        
        try:
            ibkr_client = services.get('ibkr_client')
            if not ibkr_client:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="IBKR client not available"
                )
            
            # Get open orders by accessing the IBKR client's open orders method directly
            open_orders = ibkr_client.ib.openOrders()
            account_orders = [order for order in open_orders if order.account == self.account_id]
            
            if not account_orders:
                log_with_event(logger, 'info',
                              f"No pending orders found for account {self.account_id}",
                              event_id=self.event_id, account_id=self.account_id)
            else:
                log_with_event(logger, 'info',
                              f"Pending orders for account {self.account_id}:",
                              event_id=self.event_id, account_id=self.account_id)
                
                for order in account_orders:
                    symbol = 'Unknown'
                    if hasattr(order, 'contract') and order.contract:
                        symbol = getattr(order.contract, 'symbol', 'Unknown')
                    
                    log_with_event(logger, 'info',
                                  f"  Order {order.orderId}: {order.action} {abs(order.totalQuantity)} "
                                  f"{symbol} ({order.orderType})",
                                  event_id=self.event_id, account_id=self.account_id,
                                  order_id=order.orderId, action=order.action,
                                  quantity=abs(order.totalQuantity), symbol=symbol,
                                  order_type=order.orderType)
            
            # Format order details for return
            order_details = []
            for order in account_orders:
                symbol = 'Unknown'
                if hasattr(order, 'contract') and order.contract:
                    symbol = getattr(order.contract, 'symbol', 'Unknown')
                
                order_details.append({
                    'order_id': str(order.orderId),
                    'symbol': symbol,
                    'quantity': abs(order.totalQuantity),
                    'action': order.action,
                    'order_type': order.orderType
                })
            
            return EventCommandResult(
                status=CommandStatus.SUCCESS,
                message="Print orders command executed successfully",
                data={"action": "print-orders", "orders": order_details}
            )
            
        except Exception as e:
            logger.error(f"Print orders failed: {e}", extra={
                'event_id': self.event_id,
                'account_id': self.account_id,
                'error': str(e)
            })
            
            return EventCommandResult(
                status=CommandStatus.FAILED,
                error=str(e)
            )