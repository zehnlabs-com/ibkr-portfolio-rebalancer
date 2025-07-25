import asyncio
import pandas as pd
from typing import List, Dict, Optional
from collections import defaultdict
from datetime import datetime
from app.config import config
from app.models.account_config import EventAccountConfig
from app.services.ibkr_client import IBKRClient
from app.services.allocation_service import AllocationService
from app.logger import AppLogger

app_logger = AppLogger(__name__)

class TradingHoursException(Exception):
    """Exception raised when symbols are outside trading hours"""
    
    def __init__(self, message: str, next_start_time: Optional[datetime] = None, symbol_status: Optional[Dict[str, bool]] = None):
        super().__init__(message)
        self.message = message
        self.next_start_time = next_start_time
        self.symbol_status = symbol_status or {}

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
    
    async def rebalance_account(self, account_config: EventAccountConfig, event=None):
        # Log queue position
        waiting_accounts = [acc_id for acc_id, lock in self._account_locks.items() if lock.locked()]
        if waiting_accounts:
            app_logger.log_debug(f"Account {account_config.account_id} waiting for {len(waiting_accounts)} accounts: {waiting_accounts}", event)
        
        async with self._account_locks[account_config.account_id]:
            app_logger.log_debug(f"Account {account_config.account_id} acquired lock, starting rebalance", event)
            try:
                app_logger.log_info(f"Starting LIVE rebalance for account {account_config.account_id}", event)
                
                target_allocations = await AllocationService.get_allocations(account_config, event)
                
                current_positions = await self.ibkr_client.get_positions(account_config.account_id, event)
                account_value = await self.ibkr_client.get_account_value(account_config.account_id, event=event)
                
                result = await self._calculate_rebalance_orders(
                    target_allocations, 
                    current_positions, 
                    account_value,
                    account_config,
                    event
                )
                
                # Cancel all pending orders before executing any trades
                cancelled_orders = await self._cancel_pending_orders(account_config.account_id, event)
                
                # Execute sell orders first and wait for completion
                await self._execute_sell_orders(account_config.account_id, result.orders, dry_run=False, event=event)
                
                # Execute buy orders (no cash validation - trust pandas calculations)
                await self._execute_buy_orders(account_config.account_id, result.orders, dry_run=False, event=event)
                
                app_logger.log_info(f"Completed LIVE rebalance for account {account_config.account_id}", event)
                
                # Include cancelled orders in the result
                return RebalanceResult(result.orders, result.equity_info, cancelled_orders)
                
            except Exception as e:
                app_logger.log_error(f"Error in LIVE rebalance for account {account_config.account_id}: {e}", event)
                raise
    
    async def _calculate_rebalance_orders(
        self, 
        target_allocations: List[Dict[str, float]], 
        current_positions: List[Dict], 
        account_value: float,
        account_config: EventAccountConfig,
        event=None,
        skip_trading_hours_check: bool = False
    ) -> RebalanceResult:
        
        # Calculate cash reserve scaling factor (like simple algorithm)
        cash_reserve_percent = account_config.cash_reserve_percent / 100.0
        scaling_factor = 1.0 - cash_reserve_percent
        reserve_amount = account_value * cash_reserve_percent
        
        app_logger.log_info(f"Account {account_config.account_id}: Account value: ${account_value:.2f}, Cash reserve: {account_config.cash_reserve_percent}% (${reserve_amount:.2f}), Scaling factor: {scaling_factor:.3f}", event)
        
        # Convert target allocations to DataFrame with scaled weights
        target_df = pd.DataFrame([
            {'symbol': allocation['symbol'], 'target_weight': allocation['allocation'] * scaling_factor}
            for allocation in target_allocations
        ])
        
        # Convert current positions to DataFrame  
        if current_positions:
            current_df = pd.DataFrame([{
                'symbol': pos['symbol'],
                'shares': pos['position'],
                'market_value': pos.get('market_value', 0.0)
            } for pos in current_positions])
        else:
            current_df = pd.DataFrame(columns=['symbol', 'shares', 'market_value'])
        
        # Merge target and current positions (outer join to include positions to liquidate)
        if not current_df.empty:
            portfolio_df = pd.merge(target_df, current_df, on='symbol', how='outer')
        else:
            portfolio_df = target_df.copy()
            portfolio_df['shares'] = 0
            portfolio_df['market_value'] = 0.0
        
        portfolio_df.fillna(0, inplace=True)
        
        # Calculate target values based on account value
        portfolio_df['target_value'] = account_value * portfolio_df['target_weight']
        
        # Check trading hours for all symbols before getting prices
        all_symbols = portfolio_df['symbol'].unique().tolist()
        
        if not skip_trading_hours_check:
            # Validate trading hours
            all_within_hours, next_start_time, symbol_status = await self.ibkr_client.check_trading_hours(all_symbols, event)
            
            if not all_within_hours:
                # Some symbols are outside trading hours - raise special exception
                raise TradingHoursException(
                    message="One or more symbols are outside trading hours",
                    next_start_time=next_start_time,
                    symbol_status=symbol_status
                )
        
        # Get market prices for all symbols
        market_prices = await self.ibkr_client.get_multiple_market_prices(all_symbols, event)
        
        # Validate prices
        missing_prices = [symbol for symbol in all_symbols if symbol not in market_prices]
        if missing_prices:
            raise ValueError(f"Missing market prices for symbols: {', '.join(missing_prices)}.")
        
        portfolio_df['current_price'] = portfolio_df['symbol'].map(market_prices)
        
        # Calculate trades needed (pandas vectorized operations)
        portfolio_df['value_diff'] = portfolio_df['target_value'] - portfolio_df['market_value']
        portfolio_df['shares_to_trade'] = (portfolio_df['value_diff'] / portfolio_df['current_price']).round().astype(int)
        
        # Filter to only trades that are needed
        trades_df = portfolio_df[portfolio_df['shares_to_trade'] != 0].copy()
        
        app_logger.log_info(f"\n{trades_df[['symbol', 'shares', 'market_value', 'target_value', 'value_diff', 'shares_to_trade']].to_string()}", event)
        
        # Convert to RebalanceOrder objects
        orders = []
        for _, row in trades_df.iterrows():
            shares_to_trade = int(row['shares_to_trade'])
            action = 'BUY' if shares_to_trade > 0 else 'SELL'
            quantity = abs(shares_to_trade)
            market_value = quantity * row['current_price']
            
            orders.append(RebalanceOrder(
                symbol=row['symbol'],
                quantity=quantity,
                action=action,
                market_value=market_value
            ))
        
        # Create equity info
        equity_info = {
            'total_equity': account_value,
            'cash_reserve_percent': account_config.cash_reserve_percent,
            'reserve_amount': reserve_amount,
            'available_for_trading': account_value - reserve_amount
        }
        
        return RebalanceResult(orders, equity_info)
    
    async def _cancel_pending_orders(self, account_id: str, event=None):
        """Cancel all pending orders for the account before rebalancing"""
        try:
            cancelled_orders = await self.ibkr_client.cancel_all_orders(account_id, event)
            if cancelled_orders:
                app_logger.log_info(f"Cancelled {len(cancelled_orders)} pending orders for account {account_id}", event)
            return cancelled_orders
        except Exception as e:
            app_logger.log_error(f"Failed to cancel pending orders for account {account_id}: {e}", event)
            raise

    async def _execute_sell_orders(self, account_id: str, orders: List[RebalanceOrder], dry_run: bool = False, event=None):
        """Execute sell orders with concurrent placement and concurrent waiting - fail fast on any rejection"""
        sell_orders = [order for order in orders if order.action == 'SELL']
        
        if not sell_orders:
            app_logger.log_info("No sell orders to execute", event)
            return
        
        mode_text = "DRY RUN" if dry_run else "LIVE"
        app_logger.log_info(f"{mode_text} - Executing {len(sell_orders)} sell orders for account {account_id}", event)
        
        if dry_run:
            for order in sell_orders:
                app_logger.log_info(f"DRY RUN - Would execute: {order}", event)
            return
        
        # Place ALL sell orders concurrently (like simple algorithm)
        sell_tasks = []
        for order in sell_orders:
            quantity = -order.quantity  # Negative for sell
            
            trade = await self.ibkr_client.place_order(
                account_id=account_id,
                symbol=order.symbol,
                quantity=quantity,
                order_type="MKT",
                event=event,
                time_in_force=config.order.time_in_force,
                extended_hours=config.order.extended_hours_enabled
            )
            
            sell_tasks.append(trade)
            app_logger.log_info(f"SELL order placed: {order} - Order ID: {trade.order.orderId}", event)
        
        # Wait for ALL sells to complete concurrently - any failure will fail immediately
        try:
            await asyncio.gather(*[self._wait_for_order_completion(trade, event) for trade in sell_tasks])
            app_logger.log_info("All SELL orders executed successfully", event)
        except Exception as e:
            # Any single order failure will cause this exception immediately
            app_logger.log_error(f"SELL order execution failed: {e}", event)
            raise
    
    async def _execute_buy_orders(self, account_id: str, orders: List[RebalanceOrder], dry_run: bool = False, event=None):
        """Execute buy orders with concurrent placement and concurrent waiting - fail fast on any rejection"""
        buy_orders = [order for order in orders if order.action == 'BUY']
        
        if not buy_orders:
            app_logger.log_info("No buy orders to execute", event)
            return
        
        mode_text = "DRY RUN" if dry_run else "LIVE"
        app_logger.log_info(f"{mode_text} - Executing {len(buy_orders)} buy orders for account {account_id}", event)
        
        if dry_run:
            for order in buy_orders:
                app_logger.log_info(f"DRY RUN - Would execute: {order}", event)
            return
        
        # Place ALL buy orders concurrently (like simple algorithm)
        buy_tasks = []
        for order in buy_orders:
            trade = await self.ibkr_client.place_order(
                account_id=account_id,
                symbol=order.symbol,
                quantity=order.quantity,
                order_type="MKT",
                event=event,
                time_in_force=config.order.time_in_force,
                extended_hours=config.order.extended_hours_enabled
            )
            
            buy_tasks.append(trade)
            app_logger.log_info(f"BUY order placed: {order} - Order ID: {trade.order.orderId}", event)
        
        # Wait for ALL buys to complete concurrently - any failure will fail immediately
        try:
            await asyncio.gather(*[self._wait_for_order_completion(trade, event) for trade in buy_tasks])
            app_logger.log_info("All BUY orders executed successfully", event)
        except Exception as e:
            # Any single order failure will cause this exception immediately
            app_logger.log_error(f"BUY order execution failed: {e}", event)
            raise
    
    async def _wait_for_order_completion(self, trade, event=None):
        """Wait for order to complete and fail immediately if not filled"""
        if trade.isDone():
            # Check status immediately for already completed orders
            if trade.orderStatus.status != 'Filled':
                raise Exception(f"Order {trade.order.orderId} failed with status: {trade.orderStatus.status}")
            return
        
        # Create completion event that fires on either fill or cancellation
        completion_event = asyncio.Event()
        
        def on_completion():
            completion_event.set()
        
        # Listen to both fill and cancellation events
        trade.filledEvent += on_completion
        trade.cancelledEvent += on_completion
        
        try:
            # Wait for completion with configurable timeout
            timeout = config.ibkr.order_completion_timeout
            await asyncio.wait_for(completion_event.wait(), timeout=timeout)
            
            # As soon as order completes, fail immediately if not filled
            if trade.orderStatus.status != 'Filled':
                raise Exception(f"Order {trade.order.orderId} failed with status: {trade.orderStatus.status}")
                
        except asyncio.TimeoutError:
            app_logger.log_error(f"Order {trade.order.orderId} timed out after {timeout}s - Status: {trade.orderStatus.status}", event)
            raise Exception(f"Order {trade.order.orderId} timed out after {timeout}s")
        finally:
            # Clean up event handlers
            trade.filledEvent -= on_completion
            trade.cancelledEvent -= on_completion
    
    async def dry_run_rebalance(self, account_config: EventAccountConfig, event=None) -> RebalanceResult:
        # Log queue position
        waiting_accounts = [acc_id for acc_id, lock in self._account_locks.items() if lock.locked()]
        if waiting_accounts:
            app_logger.log_debug(f"Account {account_config.account_id} waiting for {len(waiting_accounts)} accounts: {waiting_accounts}", event)
        
        async with self._account_locks[account_config.account_id]:
            app_logger.log_debug(f"Account {account_config.account_id} acquired lock, starting dry run rebalance", event)
            try:
                app_logger.log_info(f"Starting dry run rebalance for account {account_config.account_id}", event)
                
                target_allocations = await AllocationService.get_allocations(account_config, event)
                
                current_positions = await self.ibkr_client.get_positions(account_config.account_id, event)
                account_value = await self.ibkr_client.get_account_value(account_config.account_id, event=event)
                
                result = await self._calculate_rebalance_orders(
                    target_allocations, 
                    current_positions, 
                    account_value,
                    account_config,
                    event,
                    skip_trading_hours_check=True
                )
                
                # Simulate sell orders first
                await self._execute_sell_orders(account_config.account_id, result.orders, dry_run=True, event=event)
                
                # Simulate buy orders
                await self._execute_buy_orders(account_config.account_id, result.orders, dry_run=True, event=event)
                
                return result
                
            except Exception as e:
                app_logger.log_error(f"Error in dry run rebalance for account {account_config.account_id}: {e}", event)
                raise