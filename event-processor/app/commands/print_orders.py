"""
Print orders command implementation.
"""

from typing import Dict, Any
from app.commands.base import EventCommand, EventCommandResult, CommandStatus
from app.logger import AppLogger

app_logger = AppLogger(__name__)


class PrintOrdersCommand(EventCommand):
    """Command to print account orders"""
    
    def _get_command_type(self) -> str:
        return "print-orders"
    
    async def execute(self, services: Dict[str, Any]) -> EventCommandResult:
        """Execute print orders command"""
        app_logger.log_info(f"Printing pending orders for account {self.event.account_id}", self.event)
        
        try:
            ibkr_client = services.get('ibkr_client')
            if not ibkr_client:
                return EventCommandResult(
                    status=CommandStatus.FAILED,
                    error="IBKR client not available"
                )
            
            # Get open orders by accessing the IBKR client's open orders method directly
            open_orders = ibkr_client.ib.openOrders()
            account_orders = [order for order in open_orders if order.account == self.event.account_id]
            
            if not account_orders:
                app_logger.log_info(f"No pending orders found for account {self.event.account_id}", self.event)
            else:
                app_logger.log_info(f"Pending orders for account {self.event.account_id}:", self.event)
                
                for order in account_orders:
                    symbol = 'Unknown'
                    if hasattr(order, 'contract') and order.contract:
                        symbol = getattr(order.contract, 'symbol', 'Unknown')
                    
                    app_logger.log_info(f"  Order {order.orderId}: {order.action} {abs(order.totalQuantity)} {symbol} ({order.orderType})", self.event)
            
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
            app_logger.log_error(f"Print orders failed: {e}", self.event)
            
            return EventCommandResult(
                status=CommandStatus.FAILED,
                error=str(e)
            )