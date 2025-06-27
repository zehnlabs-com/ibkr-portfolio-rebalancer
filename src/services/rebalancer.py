from typing import List, Dict, Set
from decimal import Decimal, ROUND_DOWN
from ..models.portfolio import AllocationRequest, Position, Trade, RebalanceResponse, MarketData
from .ibkr_client import IBKRClient


class PortfolioRebalancer:
    def __init__(self, ibkr_client: IBKRClient, portfolio_cap: str = None):
        self.ibkr_client = ibkr_client
        self.portfolio_cap = portfolio_cap
    
    async def calculate_rebalance(self, target_allocations: List[AllocationRequest]) -> RebalanceResponse:
        """Calculate trades needed to rebalance portfolio using johnnymo87's exact algorithm"""
        try:
            # Step 1: Get current positions and portfolio value
            positions = await self.ibkr_client.get_positions()
            raw_portfolio_value = await self.ibkr_client.get_portfolio_value()
            
            if raw_portfolio_value <= 0:
                return RebalanceResponse(
                    success=False,
                    message="Portfolio has no value or positions",
                    total_portfolio_value=raw_portfolio_value
                )
            
            # Step 2: Apply portfolio cap if specified
            portfolio_value = self._apply_portfolio_cap(raw_portfolio_value)
            
            # Step 3: Get market data for all symbols (current + target)
            all_symbols = self._get_all_symbols(positions, target_allocations)
            market_data = await self.ibkr_client.get_multiple_market_data(all_symbols)
            
            # Step 4: Calculate trades using johnnymo87's logic
            trades = await self._calculate_trades_johnnymo87(positions, target_allocations, portfolio_value, market_data)
            
            return RebalanceResponse(
                success=True,
                message=f"Calculated {len(trades)} trades for rebalancing",
                trades=trades,
                total_portfolio_value=portfolio_value
            )
            
        except Exception as e:
            return RebalanceResponse(
                success=False,
                message=f"Error calculating rebalance: {str(e)}"
            )
    
    async def execute_rebalance(self, target_allocations: List[AllocationRequest]) -> RebalanceResponse:
        """Calculate and execute trades using two-phase execution"""
        try:
            # Step 1: Get current positions and portfolio value
            positions = await self.ibkr_client.get_positions()
            raw_portfolio_value = await self.ibkr_client.get_portfolio_value()
            portfolio_value = self._apply_portfolio_cap(raw_portfolio_value)
            
            # Step 2: Get market data
            all_symbols = self._get_all_symbols(positions, target_allocations)
            market_data = await self.ibkr_client.get_multiple_market_data(all_symbols)
            
            # Step 3: Calculate and execute trades in two phases
            accounts = await self.ibkr_client.get_account_info()
            if not accounts:
                return RebalanceResponse(
                    success=False,
                    message="No account found"
                )
            
            account_id = accounts[0]["id"]
            
            # Phase 1: Execute sell trades
            sell_trades = await self._calculate_sell_trades(positions, target_allocations, portfolio_value, market_data)
            executed_sells = []
            
            for trade in sorted(sell_trades, key=lambda t: t.trade_value or Decimal('0'), reverse=True):
                try:
                    order_result = await self.ibkr_client.place_order(trade, account_id)
                    if order_result:
                        executed_sells.append(trade)
                except Exception as e:
                    print(f"Failed to execute sell trade {trade.symbol}: {e}")
            
            # Phase 2: Recalculate positions and execute buy trades
            # Note: In practice, you'd wait for sells to settle before buying
            updated_positions = await self.ibkr_client.get_positions()
            updated_portfolio_value = self._apply_portfolio_cap(await self.ibkr_client.get_portfolio_value())
            
            buy_trades = await self._calculate_buy_trades(updated_positions, target_allocations, updated_portfolio_value, market_data)
            executed_buys = []
            
            for trade in sorted(buy_trades, key=lambda t: t.trade_value or Decimal('0'), reverse=True):
                try:
                    order_result = await self.ibkr_client.place_order(trade, account_id)
                    if order_result:
                        executed_buys.append(trade)
                except Exception as e:
                    print(f"Failed to execute buy trade {trade.symbol}: {e}")
            
            all_executed = executed_sells + executed_buys
            
            return RebalanceResponse(
                success=True,
                message=f"Executed {len(executed_sells)} sells and {len(executed_buys)} buys",
                trades=all_executed,
                total_portfolio_value=updated_portfolio_value
            )
            
        except Exception as e:
            return RebalanceResponse(
                success=False,
                message=f"Error executing rebalance: {str(e)}"
            )
    
    def _apply_portfolio_cap(self, portfolio_value: Decimal) -> Decimal:
        """Apply portfolio cap if specified"""
        if self.portfolio_cap is None:
            return portfolio_value
        
        if self.portfolio_cap.endswith('%'):
            cap_percent = Decimal(self.portfolio_cap[:-1]) / Decimal('100')
            return portfolio_value * cap_percent
        elif self.portfolio_cap.startswith('$'):
            cap_amount = Decimal(self.portfolio_cap[1:])
            return min(portfolio_value, cap_amount)
        else:
            raise ValueError(f"Invalid portfolio cap format: {self.portfolio_cap}")
    
    def _get_all_symbols(self, positions: List[Position], target_allocations: List[AllocationRequest]) -> List[str]:
        """Get all unique symbols from positions and target allocations"""
        symbols = set()
        
        # Add symbols from current positions
        for position in positions:
            symbols.add(position.symbol)
        
        # Add symbols from target allocations
        for allocation in target_allocations:
            symbols.add(allocation.symbol)
        
        return list(symbols)
    
    async def _calculate_trades_johnnymo87(self, positions: List[Position], target_allocations: List[AllocationRequest], 
                                          portfolio_value: Decimal, market_data: Dict[str, MarketData]) -> List[Trade]:
        """Calculate trades using johnnymo87's exact algorithm"""
        # Create position lookup
        position_map = {pos.symbol: pos for pos in positions}
        target_symbols = {alloc.symbol for alloc in target_allocations}
        
        trades = []
        
        # Phase 1: Calculate sell trades (positions not in target + excess positions)
        sell_trades = await self._calculate_sell_trades(positions, target_allocations, portfolio_value, market_data)
        trades.extend(sell_trades)
        
        # Phase 2: Calculate buy trades (target positions that need more shares)
        buy_trades = await self._calculate_buy_trades(positions, target_allocations, portfolio_value, market_data)
        trades.extend(buy_trades)
        
        # Sort by trade value (largest first) - johnnymo87's prioritization
        trades.sort(key=lambda t: t.trade_value or Decimal('0'), reverse=True)
        
        return trades
    
    async def _calculate_sell_trades(self, positions: List[Position], target_allocations: List[AllocationRequest],
                                   portfolio_value: Decimal, market_data: Dict[str, MarketData]) -> List[Trade]:
        """Calculate sell trades - positions not in target + excess positions"""
        position_map = {pos.symbol: pos for pos in positions}
        target_symbols = {alloc.symbol for alloc in target_allocations}
        target_map = {alloc.symbol: alloc for alloc in target_allocations}
        
        trades = []
        
        for position in positions:
            symbol = position.symbol
            current_quantity = position.quantity
            
            if symbol not in market_data:
                continue  # Skip if no market data
            
            market = market_data[symbol]
            
            if symbol not in target_symbols:
                # Sell entire position (not in target allocation)
                if current_quantity > 0:
                    trades.append(Trade(
                        symbol=symbol,
                        action="SELL",
                        quantity=current_quantity,
                        order_type="LMT",
                        price=market.bid,
                        trade_value=current_quantity * market.bid
                    ))
            else:
                # Calculate target quantity and sell excess if any
                target_allocation = target_map[symbol]
                target_value = portfolio_value * target_allocation.allocation
                target_quantity = target_value / market.last
                
                if current_quantity > target_quantity:
                    excess_quantity = current_quantity - target_quantity
                    if excess_quantity >= Decimal('0.01'):  # Minimum trade threshold
                        trades.append(Trade(
                            symbol=symbol,
                            action="SELL",
                            quantity=excess_quantity,
                            order_type="LMT",
                            price=market.bid,
                            trade_value=excess_quantity * market.bid
                        ))
        
        return trades
    
    async def _calculate_buy_trades(self, positions: List[Position], target_allocations: List[AllocationRequest],
                                  portfolio_value: Decimal, market_data: Dict[str, MarketData]) -> List[Trade]:
        """Calculate buy trades - target positions that need more shares"""
        position_map = {pos.symbol: pos for pos in positions}
        
        trades = []
        
        for target_allocation in target_allocations:
            symbol = target_allocation.symbol
            
            if symbol not in market_data:
                continue  # Skip if no market data
            
            market = market_data[symbol]
            current_quantity = position_map.get(symbol, Position(symbol=symbol, quantity=Decimal('0'), market_value=Decimal('0'), avg_cost=Decimal('0'))).quantity
            
            # Calculate target quantity
            target_value = portfolio_value * target_allocation.allocation
            target_quantity = target_value / market.last
            
            if target_quantity > current_quantity:
                shortage_quantity = target_quantity - current_quantity
                if shortage_quantity >= Decimal('0.01'):  # Minimum trade threshold
                    trades.append(Trade(
                        symbol=symbol,
                        action="BUY",
                        quantity=shortage_quantity,
                        order_type="LMT",
                        price=market.ask,
                        trade_value=shortage_quantity * market.ask
                    ))
        
        return trades