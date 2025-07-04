import math
import asyncio
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from app.config import AccountConfig, config
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

class RebalanceResult:
    def __init__(self, orders, equity_info, cancelled_orders=None):
        self.orders = orders
        self.equity_info = equity_info
        self.cancelled_orders = cancelled_orders or []

class RebalancerService:
    # Class-level locks shared across all instances
    _account_locks = defaultdict(asyncio.Lock)
    
    def __init__(self, ibkr_client: IBKRClient):
        self.ibkr_client = ibkr_client
    
    async def rebalance_account(self, account_config: AccountConfig, order_type: str = "MKT"):
        # Log queue position
        waiting_accounts = [acc_id for acc_id, lock in self._account_locks.items() if lock.locked()]
        if waiting_accounts:
            logger.info(f"Account {account_config.account_id} waiting for {len(waiting_accounts)} accounts: {waiting_accounts}")
        
        async with self._account_locks[account_config.account_id]:
            logger.info(f"Account {account_config.account_id} acquired lock, starting rebalance")
            try:
                logger.info(f"Starting LIVE rebalance for account {account_config.account_id}")
                
                target_allocations = AllocationService.get_allocations(account_config)
                
                current_positions = await self.ibkr_client.get_positions(account_config.account_id)
                account_value = await self.ibkr_client.get_account_value(account_config.account_id)
                
                result = await self._calculate_rebalance_orders(
                    target_allocations, 
                    current_positions, 
                    account_value,
                    account_config
                )
                
                cancelled_orders = await self._execute_orders(account_config.account_id, result.orders, order_type, dry_run=False)
                
                logger.info(f"Completed LIVE rebalance for account {account_config.account_id}")
                
                # Include cancelled orders in the result
                return RebalanceResult(result.orders, result.equity_info, cancelled_orders)
                
            except Exception as e:
                logger.error(f"Error in LIVE rebalance for account {account_config.account_id}: {e}")
                raise
    
    async def _calculate_rebalance_orders(
        self, 
        target_allocations: List[Dict[str, float]], 
        current_positions: List[Dict], 
        account_value: float,
        account_config: AccountConfig
    ) -> RebalanceResult:
        
        orders = []
        
        # Calculate available equity after reserve
        reserve_percentage = account_config.rebalancing.equity_reserve_percentage / 100.0
        reserve_amount = account_value * reserve_percentage
        available_equity = account_value * (1.0 - reserve_percentage)
        
        # Create equity info
        equity_info = {
            'total_equity': account_value,
            'reserve_percentage': account_config.rebalancing.equity_reserve_percentage,
            'reserve_amount': reserve_amount,
            'available_for_trading': available_equity
        }
        
        logger.info(f"Account {account_config.account_id}: Account value: ${account_value:.2f}, Reserve: {account_config.rebalancing.equity_reserve_percentage}% (${reserve_amount:.2f}), Available for trading: ${available_equity:.2f}")
        
        current_positions_map = {pos['symbol']: pos for pos in current_positions}
        
        target_positions = {}
        for allocation in target_allocations:
            symbol = allocation['symbol']
            target_percentage = allocation['allocation']
            target_value = available_equity * target_percentage
            target_positions[symbol] = target_value
        
        all_symbols = set()
        all_symbols.update(target_positions.keys())
        all_symbols.update(current_positions_map.keys())
        
        # Get all market prices in parallel for better performance
        # Retry logic is now handled by IBKRClient with configurable parameters
        market_prices = await self.ibkr_client.get_multiple_market_prices(list(all_symbols))
        
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
        
        return RebalanceResult(orders, equity_info)
    
    async def _cancel_pending_orders(self, account_id: str):
        """Cancel all pending orders for the account before rebalancing"""
        try:
            cancelled_orders = await self.ibkr_client.cancel_all_orders(account_id)
            if cancelled_orders:
                logger.info(f"Cancelled {len(cancelled_orders)} pending orders for account {account_id}")
            return cancelled_orders
        except Exception as e:
            logger.error(f"Failed to cancel pending orders for account {account_id}: {e}")
            raise

    async def _execute_orders(self, account_id: str, orders: List[RebalanceOrder], order_type: str = "MKT", dry_run: bool = False):
        cancelled_orders = []
        
        if not dry_run:
            cancelled_orders = await self._cancel_pending_orders(account_id)
        
        if not orders:
            logger.info("No orders to execute")
            return cancelled_orders
        
        mode_text = "DRY RUN" if dry_run else "LIVE"
        logger.info(f"{mode_text} - Executing {len(orders)} orders for account {account_id} with order type {order_type}")
        
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
                        order_type=order_type
                    )
                    
                    logger.info(f"LIVE - Order placed: {order} - Order ID: {order_id}")
                
            except Exception as e:
                error_text = f"Failed to {'simulate' if dry_run else 'place'} order {order}: {e}"
                logger.error(error_text)
        
        return cancelled_orders
    
    async def dry_run_rebalance(self, account_config: AccountConfig) -> RebalanceResult:
        # Log queue position
        waiting_accounts = [acc_id for acc_id, lock in self._account_locks.items() if lock.locked()]
        if waiting_accounts:
            logger.info(f"Account {account_config.account_id} waiting for {len(waiting_accounts)} accounts: {waiting_accounts}")
        
        async with self._account_locks[account_config.account_id]:
            logger.info(f"Account {account_config.account_id} acquired lock, starting dry run rebalance")
            try:
                logger.info(f"Starting dry run rebalance for account {account_config.account_id}")
                
                target_allocations = AllocationService.get_allocations(account_config)
                
                current_positions = await self.ibkr_client.get_positions(account_config.account_id)
                account_value = await self.ibkr_client.get_account_value(account_config.account_id)
                
                result = await self._calculate_rebalance_orders(
                    target_allocations, 
                    current_positions, 
                    account_value,
                    account_config
                )
                
                await self._execute_orders(account_config.account_id, result.orders, "MKT", dry_run=True)
                
                return result
                
            except Exception as e:
                logger.error(f"Error in dry run rebalance for account {account_config.account_id}: {e}")
                raise