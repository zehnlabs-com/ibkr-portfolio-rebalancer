import math
import asyncio
from typing import List, Dict, Optional, Tuple
from app.config import AccountConfig
from app.services.ibkr_client import IBKRClient
from app.services.allocation_service import AllocationService
from app.logger import setup_logger

logger = setup_logger(__name__)

class RebalanceOrder:
    def __init__(self, symbol: str, quantity: int, action: str, market_value: float):
        self.symbol = symbol
        self.quantity = abs(quantity)
        self.action = action  # 'BUY' or 'SELL'
        self.market_value = market_value
    
    def __repr__(self):
        return f"{self.action} {self.quantity} shares of {self.symbol} (${self.market_value:.2f})"

class RebalancerService:
    def __init__(self, ibkr_client: IBKRClient):
        self.ibkr_client = ibkr_client
    
    async def rebalance_account(self, account_config: AccountConfig, dry_run: bool = True):
        mode_text = "DRY RUN" if dry_run else "LIVE"
        try:
            logger.info(f"Starting {mode_text} rebalance for account {account_config.account_id}")
            
            target_allocations = await AllocationService.get_allocations(account_config)
            
            current_positions = await self.ibkr_client.get_positions(account_config.account_id)
            account_value = await self.ibkr_client.get_account_value(account_config.account_id)
            
            orders = await self._calculate_rebalance_orders(
                target_allocations, 
                current_positions, 
                account_value
            )
            
            await self._execute_orders(account_config.account_id, orders, dry_run=dry_run)
            
            logger.info(f"Completed {mode_text} rebalance for account {account_config.account_id}")
            
            return orders
            
        except Exception as e:
            logger.error(f"Error in {mode_text} rebalance for account {account_config.account_id}: {e}")
            raise
    
    async def _calculate_rebalance_orders(
        self, 
        target_allocations: List[Dict[str, float]], 
        current_positions: List[Dict], 
        account_value: float
    ) -> List[RebalanceOrder]:
        
        orders = []
        
        current_positions_map = {pos['symbol']: pos for pos in current_positions}
        
        target_positions = {}
        for allocation in target_allocations:
            symbol = allocation['symbol']
            target_percentage = allocation['allocation']
            target_value = account_value * target_percentage
            target_positions[symbol] = target_value
        
        all_symbols = set()
        all_symbols.update(target_positions.keys())
        all_symbols.update(current_positions_map.keys())
        
        # Get all market prices in parallel for better performance
        # Retry logic for market data readiness after startup
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                market_prices = await self.ibkr_client.get_multiple_market_prices(list(all_symbols))
                break
            except Exception as e:
                if attempt < max_retries - 1 and "Failed to get prices" in str(e):
                    logger.warning(f"Market data not ready (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s: {e}")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Failed to get market prices: {e}")
                    raise
        
        for symbol, target_value in target_positions.items():
            if symbol not in market_prices:
                logger.warning(f"No market price available for {symbol}, skipping")
                continue
            
            market_price = market_prices[symbol]
            target_shares = target_value / market_price
            
            current_shares = 0
            if symbol in current_positions_map:
                current_shares = current_positions_map[symbol]['position']
            
            shares_diff = target_shares - current_shares
            
            if abs(shares_diff) > 0.5:
                shares_to_trade = int(round(shares_diff))
                
                if shares_to_trade > 0:
                    orders.append(RebalanceOrder(
                        symbol=symbol,
                        quantity=shares_to_trade,
                        action='BUY',
                        market_value=shares_to_trade * market_price
                    ))
                else:
                    orders.append(RebalanceOrder(
                        symbol=symbol,
                        quantity=abs(shares_to_trade),
                        action='SELL',
                        market_value=abs(shares_to_trade) * market_price
                    ))
        
        for symbol, position in current_positions_map.items():
            if symbol not in target_positions and position['position'] > 0:
                if symbol in market_prices:
                    market_price = market_prices[symbol]
                    shares_to_sell = int(position['position'])
                    
                    orders.append(RebalanceOrder(
                        symbol=symbol,
                        quantity=shares_to_sell,
                        action='SELL',
                        market_value=shares_to_sell * market_price
                    ))
        
        return orders
    
    async def _execute_orders(self, account_id: str, orders: List[RebalanceOrder], dry_run: bool = False):
        if not orders:
            logger.info("No orders to execute")
            return
        
        mode_text = "DRY RUN" if dry_run else "LIVE"
        logger.info(f"{mode_text} - Executing {len(orders)} orders for account {account_id}")
        
        for order in orders:
            try:
                if dry_run:
                    logger.info(f"DRY RUN - Would execute: {order}")
                else:
                    quantity = order.quantity if order.action == 'BUY' else -order.quantity
                    
                    order_id = await self.ibkr_client.place_order(
                        account_id=account_id,
                        symbol=order.symbol,
                        quantity=quantity,
                        order_type='MKT'
                    )
                    
                    logger.info(f"LIVE - Order placed: {order} - Order ID: {order_id}")
                
            except Exception as e:
                error_text = f"Failed to {'simulate' if dry_run else 'place'} order {order}: {e}"
                logger.error(error_text)
    
    async def dry_run_rebalance(self, account_config: AccountConfig) -> List[RebalanceOrder]:
        try:
            logger.info(f"Starting dry run rebalance for account {account_config.account_id}")
            
            target_allocations = await AllocationService.get_allocations(account_config)
            
            current_positions = await self.ibkr_client.get_positions(account_config.account_id)
            account_value = await self.ibkr_client.get_account_value(account_config.account_id)
            
            orders = await self._calculate_rebalance_orders(
                target_allocations, 
                current_positions, 
                account_value
            )
            
            await self._execute_orders(account_config.account_id, orders, dry_run=True)
            
            return orders
            
        except Exception as e:
            logger.error(f"Error in dry run rebalance for account {account_config.account_id}: {e}")
            raise