import math
import asyncio
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from app.config import config
from app.models.account_config import EventAccountConfig
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
    
    async def rebalance_account(self, account_config: EventAccountConfig):
        # Log queue position
        waiting_accounts = [acc_id for acc_id, lock in self._account_locks.items() if lock.locked()]
        if waiting_accounts:
            logger.debug(f"Account {account_config.account_id} waiting for {len(waiting_accounts)} accounts: {waiting_accounts}")
        
        async with self._account_locks[account_config.account_id]:
            logger.debug(f"Account {account_config.account_id} acquired lock, starting rebalance")
            try:
                logger.info(f"Starting LIVE rebalance for account {account_config.account_id}")
                
                target_allocations = await AllocationService.get_allocations(account_config)
                
                current_positions = await self.ibkr_client.get_positions(account_config.account_id)
                account_value = await self.ibkr_client.get_account_value(account_config.account_id)
                
                result = await self._calculate_rebalance_orders(
                    target_allocations, 
                    current_positions, 
                    account_value,
                    account_config
                )
                
                # Validate all orders before placing any
                await self._validate_all_orders(account_config.account_id, result.orders)
                
                # Execute sell orders first and wait for completion
                cancelled_orders = await self._execute_sell_orders(account_config.account_id, result.orders, dry_run=False)
                
                # Get actual cash balance after sells complete
                available_cash = await self.ibkr_client.get_cash_balance(account_config.account_id)
                
                # Execute buy orders with cash reserve applied
                executed_buy_orders = await self._execute_buy_orders(
                    account_config.account_id, 
                    result.orders, 
                    available_cash, 
                    account_config.rebalancing.cash_reserve_percentage,
                    account_value,
                    dry_run=False
                )
                
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
        account_config: EventAccountConfig
    ) -> RebalanceResult:
        
        orders = []
        
        # Calculate investable amount (account value minus reserve)
        reserve_amount = account_value * (account_config.rebalancing.cash_reserve_percentage / 100.0)
        investable_amount = account_value - reserve_amount
        
        logger.info(f"Account {account_config.account_id}: Account value: ${account_value:.2f}, Cash reserve: {account_config.rebalancing.cash_reserve_percentage}% (${reserve_amount:.2f}), Investable amount: ${investable_amount:.2f}")
        
        current_positions_map = {pos['symbol']: pos for pos in current_positions}
        
        target_positions = {}
        for allocation in target_allocations:
            symbol = allocation['symbol']
            target_percentage = allocation['allocation']
            target_value = investable_amount * target_percentage  # Use investable amount
            target_positions[symbol] = target_value
        
        # Create equity info (reserve info will be updated after sells)
        equity_info = {
            'total_equity': account_value,
            'cash_reserve_percentage': account_config.rebalancing.cash_reserve_percentage,
            'reserve_amount': 0,  # Will be calculated after sells
            'available_for_trading': account_value
        }
        
        all_symbols = set()
        all_symbols.update(target_positions.keys())
        all_symbols.update(current_positions_map.keys())
        
        # Get all market prices in parallel for better performance
        # Retry logic is now handled by IBKRClient with configurable parameters
        market_prices = await self.ibkr_client.get_multiple_market_prices(list(all_symbols))
        
        # Validate that we have prices for all required symbols
        missing_prices = [symbol for symbol in all_symbols if symbol not in market_prices]
        if missing_prices:
            raise ValueError(f"Missing market prices for symbols: {', '.join(missing_prices)}.")
        
        for symbol, target_value in target_positions.items():
            
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
    
    async def _validate_all_orders(self, account_id: str, orders: List[RebalanceOrder]):
        """Validate all orders using WhatIf before placing any real orders.
        
        This ensures that all orders will be accepted before we start placing them.
        If any order fails validation, the entire rebalance fails.
        """
        if not orders:
            return
            
        logger.info(f"Validating {len(orders)} orders for account {account_id}")
        
        # Convert RebalanceOrder objects to validation format
        order_data = []
        for order in orders:
            quantity = order.quantity if order.action == 'BUY' else -order.quantity
            order_data.append({
                'symbol': order.symbol,
                'quantity': quantity,
                'order_type': 'MKT',
                'time_in_force': config.order.time_in_force,
                'extended_hours': config.order.extended_hours_enabled
            })
        
        try:
            # Validate all orders in batch - this will raise exception if any fail
            validation_results = await self.ibkr_client.validate_orders_batch(account_id, order_data)
            
            # Log validation results
            total_margin_impact = 0
            total_commission = 0
            for i, result in enumerate(validation_results):
                order = orders[i]
                total_margin_impact += result['margin_after'] - result['margin_before']
                total_commission += result['commission']
                
                logger.info(f"Order validation passed: {order.symbol} - Margin impact: ${result['margin_after'] - result['margin_before']:.2f}, Commission: ${result['commission']:.2f}")
            
            logger.info(f"All orders validated successfully. Total margin impact: ${total_margin_impact:.2f}, Total commission: ${total_commission:.2f}")
            
        except Exception as e:
            logger.error(f"Order validation failed: {e}")
            raise Exception(f"Order validation failed, rebalance aborted: {e}")
    
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

    async def _execute_sell_orders(self, account_id: str, orders: List[RebalanceOrder], dry_run: bool = False):
        """Execute sell orders and wait for completion"""
        cancelled_orders = []
        
        if not dry_run:
            cancelled_orders = await self._cancel_pending_orders(account_id)
        
        sell_orders = [order for order in orders if order.action == 'SELL']
        
        if not sell_orders:
            logger.info("No sell orders to execute")
            return cancelled_orders
        
        mode_text = "DRY RUN" if dry_run else "LIVE"
        logger.info(f"{mode_text} - Executing {len(sell_orders)} sell orders for account {account_id}")
        
        sell_order_ids = []
        
        for order in sell_orders:
            try:
                if dry_run:
                    logger.info(f"DRY RUN - Would execute: {order}")
                else:
                    quantity = -order.quantity  # Negative for sell
                    
                    order_id = await self.ibkr_client.place_order(
                        account_id=account_id,
                        symbol=order.symbol,
                        quantity=quantity,
                        order_type="MKT",
                        time_in_force=config.order.time_in_force,
                        extended_hours=config.order.extended_hours_enabled
                    )
                    
                    sell_order_ids.append(str(order_id))
                    logger.info(f"LIVE - Sell order placed: {order} - Order ID: {order_id}")
                
            except Exception as e:
                error_text = f"Failed to {'simulate' if dry_run else 'place'} sell order {order}: {e}"
                logger.error(error_text)
                raise Exception(error_text) from e
        
        # Wait for sell orders to complete before returning
        if not dry_run and sell_order_ids:
            await self.ibkr_client.wait_for_sell_orders_completion(account_id, sell_order_ids)
        
        return cancelled_orders
    
    async def _execute_buy_orders(self, account_id: str, orders: List[RebalanceOrder], available_cash: float, reserve_percentage: float, account_value: float, dry_run: bool = False):
        """Execute buy orders up to available cash after reserve"""
        buy_orders = [order for order in orders if order.action == 'BUY']
        
        if not buy_orders:
            logger.info("No buy orders to execute")
            return
        
        # Calculate cash available for purchases after reserve (based on total account value)
        reserve_amount = account_value * (reserve_percentage / 100.0)
        cash_after_reserve = available_cash - reserve_amount
        
        # Sort buy orders by market value (largest first) to prioritize important positions
        buy_orders.sort(key=lambda x: x.market_value, reverse=True)
        
        mode_text = "DRY RUN" if dry_run else "LIVE"
        logger.info(f"{mode_text} - Available cash: ${available_cash:.2f}, Reserve: {reserve_percentage}% (${reserve_amount:.2f}), Cash for purchases: ${cash_after_reserve:.2f}")
        
        executed_orders = []
        total_cost = 0.0
        
        for order in buy_orders:
            if total_cost + order.market_value <= cash_after_reserve:
                try:
                    if dry_run:
                        logger.info(f"DRY RUN - Would execute: {order}")
                    else:
                        order_id = await self.ibkr_client.place_order(
                            account_id=account_id,
                            symbol=order.symbol,
                            quantity=order.quantity,
                            order_type="MKT",
                            time_in_force=config.order.time_in_force,
                            extended_hours=config.order.extended_hours_enabled
                        )
                        
                        logger.info(f"LIVE - Buy order placed: {order} - Order ID: {order_id}")
                    
                    executed_orders.append(order)
                    total_cost += order.market_value
                    
                except Exception as e:
                    error_text = f"Failed to {'simulate' if dry_run else 'place'} buy order {order}: {e}"
                    logger.error(error_text)
                    raise Exception(error_text) from e
            else:
                logger.info(f"Skipping buy order {order} - insufficient cash (need ${order.market_value:.2f}, have ${cash_after_reserve - total_cost:.2f} remaining)")
        
        logger.info(f"{mode_text} - Executed {len(executed_orders)} buy orders totaling ${total_cost:.2f}")
        return executed_orders
    
    async def dry_run_rebalance(self, account_config: EventAccountConfig) -> RebalanceResult:
        # Log queue position
        waiting_accounts = [acc_id for acc_id, lock in self._account_locks.items() if lock.locked()]
        if waiting_accounts:
            logger.debug(f"Account {account_config.account_id} waiting for {len(waiting_accounts)} accounts: {waiting_accounts}")
        
        async with self._account_locks[account_config.account_id]:
            logger.debug(f"Account {account_config.account_id} acquired lock, starting dry run rebalance")
            try:
                logger.info(f"Starting dry run rebalance for account {account_config.account_id}")
                
                target_allocations = await AllocationService.get_allocations(account_config)
                
                current_positions = await self.ibkr_client.get_positions(account_config.account_id)
                account_value = await self.ibkr_client.get_account_value(account_config.account_id)
                
                result = await self._calculate_rebalance_orders(
                    target_allocations, 
                    current_positions, 
                    account_value,
                    account_config
                )
                
                # Simulate sell orders first
                await self._execute_sell_orders(account_config.account_id, result.orders, dry_run=True)
                
                # For dry run, simulate current cash balance (assume some cash from current positions)
                estimated_cash = sum(pos.get('market_value', 0) for pos in current_positions if pos.get('market_value', 0) > 0) * 0.1  # Rough estimate
                
                # Simulate buy orders with cash reserve
                await self._execute_buy_orders(
                    account_config.account_id, 
                    result.orders, 
                    estimated_cash, 
                    account_config.rebalancing.cash_reserve_percentage,
                    account_value,
                    dry_run=True
                )
                
                return result
                
            except Exception as e:
                logger.error(f"Error in dry run rebalance for account {account_config.account_id}: {e}")
                raise