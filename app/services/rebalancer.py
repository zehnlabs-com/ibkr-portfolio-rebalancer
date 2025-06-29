from app.services.ibkr_service import IBKRService
from app.models import AllocationRequest, CalculatedOrder
from typing import List, Dict
import math
from loguru import logger

class PortfolioRebalancer:
    def __init__(self, ibkr_service: IBKRService):
        self.ibkr_service = ibkr_service
    
    async def calculate_orders(self, target_allocations: List[AllocationRequest]) -> Dict:
        """
        Calculate required orders without executing them
        Returns orders in execution order (sells first, then buys)
        """
        try:
            # 1. Get current account value
            account_value = await self.ibkr_service.get_account_value()
            logger.info(f"Total account value: ${account_value:,.2f}")
            
            # 2. Get current positions
            current_positions = await self.ibkr_service.get_positions()
            logger.info(f"Current positions: {current_positions}")
            
            # 3. Calculate orders for each symbol
            orders = []
            for allocation in target_allocations:
                symbol = allocation.symbol
                target_allocation = allocation.allocation
                
                # Get current market price
                current_price = await self.ibkr_service.get_current_price(symbol)
                
                # Calculate values
                target_value = account_value * target_allocation
                current_position = current_positions.get(symbol, {})
                current_shares = current_position.get('shares', 0)
                current_value = current_position.get('market_value', 0)
                
                # Calculate target shares
                target_shares = int(target_value / current_price)
                shares_difference = target_shares - current_shares
                
                # Only create order if meaningful difference (avoid tiny trades)
                if abs(shares_difference) > 0:
                    side = "buy" if shares_difference > 0 else "sell"
                    quantity = abs(shares_difference)
                    
                    order = CalculatedOrder(
                        side=side,
                        ticker=symbol,
                        price=current_price,
                        quantity=quantity,
                        allocation=target_allocation,
                        current_value=current_value,
                        target_value=target_value
                    )
                    orders.append(order)
            
            # 4. Sort orders: sells first, then buys (to free up cash before purchasing)
            orders.sort(key=lambda x: (x.side == "buy", x.ticker))
            
            return {
                'success': True,
                'message': f'Calculated {len(orders)} orders',
                'total_portfolio_value': account_value,
                'orders': orders
            }
            
        except Exception as e:
            logger.error(f"Error calculating orders: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to calculate orders: {str(e)}',
                'total_portfolio_value': 0.0,
                'orders': []
            }
    
    async def execute_rebalance(self, target_allocations: List[AllocationRequest]) -> Dict:
        """Execute portfolio rebalancing"""
        try:
            # First calculate the orders
            calculation_result = await self.calculate_orders(target_allocations)
            
            if not calculation_result['success']:
                return {
                    'success': False,
                    'message': calculation_result['message'],
                    'trades_executed': []
                }
            
            orders = calculation_result['orders']
            executed_trades = []
            
            # Execute each order
            for order in orders:
                await self.ibkr_service.place_order(
                    symbol=order.ticker,
                    quantity=order.quantity,
                    action=order.side.upper()
                )
                
                # Convert to dict format for response
                trade_info = {
                    'symbol': order.ticker,
                    'action': order.side.upper(),
                    'quantity': order.quantity,
                    'price': order.price,
                    'allocation': order.allocation
                }
                executed_trades.append(trade_info)
                logger.info(f"Executed: {order.side.upper()} {order.quantity} {order.ticker} @ ${order.price}")
            
            return {
                'success': True,
                'message': f'Successfully executed {len(executed_trades)} trades',
                'trades_executed': executed_trades
            }
            
        except Exception as e:
            logger.error(f"Rebalancing failed: {str(e)}")
            return {
                'success': False,
                'message': f'Rebalancing failed: {str(e)}',
                'trades_executed': []
            }