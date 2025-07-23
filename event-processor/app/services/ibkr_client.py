import asyncio
import math
import random
from typing import List, Dict, Optional, Tuple, Any
from ib_async import IB, Stock, MarketOrder, Contract
from app.config import config
from app.logger import AppLogger

app_logger = AppLogger(__name__)
class IBKRClient:
    def __init__(self):
        self.ib = IB()
        self.ib.RequestTimeout = 10.0  # Match rebalancer-api timeout
        
        # Use fixed client ID from environment (like the working old code)
        self.client_id = random.randint(1000, 2999)
        self.connected = False
        self.retry_count = 0
        self._reconnection_task = None
        
        # Add synchronization locks
        self._connection_lock = asyncio.Lock()
        self._order_lock = asyncio.Lock()
        
        
        # Set up event handlers for automatic reconnection
        self.ib.disconnectedEvent += self._on_disconnected
        self.ib.connectedEvent += self._on_connected
    
    async def connect(self) -> bool:
        if self.ib.isConnected():  # This method is synchronous and safe to use
            self.connected = True
            return True
        
        try:
            # Direct connection like the old working code
            app_logger.log_debug(f"Attempting to connect to IB Gateway at {config.ibkr.host}:{config.ibkr.port} with client ID {self.client_id}")
            await self.ib.connectAsync(
                host=config.ibkr.host,
                port=config.ibkr.port,
                clientId=self.client_id,
                timeout=10  # Use same timeout as old working code
            )
            app_logger.log_debug(f"Successfully connected to IB Gateway at {config.ibkr.host}:{config.ibkr.port}")
            self.connected = True
            return True
        except TimeoutError as e:
            app_logger.log_error(f"Connection timeout to IB Gateway at {config.ibkr.host}:{config.ibkr.port}: {e}")
            return False
        except ConnectionRefusedError as e:
            app_logger.log_error(f"Connection refused to IB Gateway at {config.ibkr.host}:{config.ibkr.port}: {e}")
            return False
        except Exception as e:
            app_logger.log_error(f"Failed to connect to IB Gateway at {config.ibkr.host}:{config.ibkr.port}: {type(e).__name__}: {e}")
            return False    
    
    def _on_disconnected(self):
        """Called automatically when connection is lost"""
        app_logger.log_warning("IBKR connection lost")
        self.connected = False
        
        # Start reconnection task if not already running
        if self._reconnection_task is None or self._reconnection_task.done():
            self._reconnection_task = asyncio.create_task(self._reconnect_loop())

    def _on_connected(self):
        """Called automatically when connection is established"""
        app_logger.log_info("IBKR connection established")
        self.connected = True

    async def _reconnect_loop(self):
        """Continuously try to reconnect every 10 seconds"""
        while not self.ib.isConnected():
            try:
                app_logger.log_info("Attempting to reconnect to IBKR...")
                await self.ib.connectAsync(
                    host=config.ibkr.host,
                    port=config.ibkr.port,
                    clientId=self.client_id,
                    timeout=10
                )
                app_logger.log_info("Reconnection successful")
                break
            except Exception as e:
                app_logger.log_warning(f"Reconnection failed: {e}, retrying in 10 seconds...")
                await asyncio.sleep(10)
    
    async def disconnect(self):
        try:
            # Cancel any ongoing reconnection task
            if self._reconnection_task and not self._reconnection_task.done():
                self._reconnection_task.cancel()
                
            if self.ib.isConnected():                
                self.ib.disconnect()
                self.connected = False
                app_logger.log_debug("Disconnected from IBKR")
        except Exception as e:
            # Some ib_async internal errors during disconnect are expected
            app_logger.log_debug(f"Disconnect error (ignored): {e}")
            pass
    
    async def __aenter__(self):
        """Async context manager entry - connect to IB"""
        # ib_async handles event loop automatically - no manual setup needed
        
        success = await self.connect()
        if not success:
            raise Exception("Failed to connect to IBKR")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - disconnect from IB"""
        await self.disconnect()
    
    async def health_check(self) -> Dict[str, Any]:
        """Simple health check that verifies IB connection is working"""
        try:
            accounts = self.ib.managedAccounts()
            return {
                "status": "healthy",
                "connected": True,
                "accounts": list(accounts),
                "client_id": self.client_id
            }
        except Exception as e:
            app_logger.log_error(f"Health check failed: {e}")
            return {
                "status": "unhealthy", 
                "connected": False,
                "error": str(e),
                "client_id": self.client_id
            }
    
    async def get_account_value(self, account_id: str, tag: str = "NetLiquidation", event=None) -> float:
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        try:
            # Use accountSummaryAsync like simple algorithm, but filter by account
            account_summary = await self.ib.accountSummaryAsync()
            for av in account_summary:
                if av.tag == tag and av.currency == "USD" and av.account == account_id:
                    return float(av.value)
            
            # If not found in summary, raise error like simple algorithm
            if tag == "NetLiquidation":
                raise Exception(f"Could not retrieve {tag} value for account {account_id} from IB.")
            return 0.0
        except Exception as e:
            app_logger.log_error(f"Failed to get account value: {e}", event)
            raise
    
    async def get_cash_balance(self, account_id: str) -> float:
        """Get available cash balance for the account"""
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        try:
            account_values = self.ib.accountValues(account_id)
            # Try TotalCashValue first, fall back to AvailableFunds
            for av in account_values:
                if av.tag == "TotalCashValue" and av.currency == "USD":
                    return float(av.value)
            
            # Fallback to AvailableFunds if TotalCashValue not found
            for av in account_values:
                if av.tag == "AvailableFunds" and av.currency == "USD":
                    return float(av.value)
            
            return 0.0
        except Exception as e:
            app_logger.log_error(f"Failed to get cash balance: {e}")
            raise
    
    async def get_positions(self, account_id: str, event=None) -> List[Dict]:
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        try:
            portfolio_items = self.ib.portfolio()
            result = []
            
            for item in portfolio_items:
                if hasattr(item, 'account') and item.account == account_id:
                    result.append({
                        'symbol': item.contract.symbol,
                        'position': item.position,
                        'market_value': item.marketValue,
                        'avg_cost': item.averageCost
                    })
            
            return result
        except Exception as e:
            app_logger.log_error(f"Failed to get positions: {e}", event)
            raise
    
    
    async def get_market_price(self, symbol: str) -> float:
        """Get market price for a single symbol"""
        prices = await self.get_multiple_market_prices([symbol])
        return prices[symbol]
    
    
    async def _fetch_single_snapshot_price(self, contract: 'Contract') -> Optional[Tuple[str, float]]:
        """
        Phase 1 helper: Fetches a price for one contract using a snapshot.
        Improved error handling to avoid Error 300 issues.
        """
        ticker = None
        try:
            # Ensure contract is properly qualified to avoid Error 300
            if not hasattr(contract, 'conId') or not contract.conId:
                app_logger.log_warning(f"Contract {contract.symbol} not properly qualified, skipping snapshot")
                return None
                
            # Request market data snapshot
            ticker = self.ib.reqMktData(
                contract, genericTickList="", snapshot=True, regulatorySnapshot=False
            )
            
            if not ticker:
                app_logger.log_warning(f"Failed to create ticker for {contract.symbol}")
                return None
            
            price = float('nan')
            
            # Wait for ticker data with more generous timeout during market hours
            max_wait_time = 30  # 3 seconds total (30 * 0.1s)
            for i in range(max_wait_time):
                await asyncio.sleep(0.1)
                
                # Check for valid market data in priority order
                market_p = ticker.marketPrice()
                last_p = ticker.last
                close_p = ticker.close
                bid_p = ticker.bid
                ask_p = ticker.ask
                
                # Prefer live market price, then last trade, then mid-point of bid/ask, then close
                if not math.isnan(market_p) and market_p > 0:
                    price = market_p
                    break
                elif last_p and not math.isnan(last_p) and last_p > 0:
                    price = last_p
                    break
                elif (bid_p and ask_p and not math.isnan(bid_p) and not math.isnan(ask_p) 
                      and bid_p > 0 and ask_p > 0):
                    price = (bid_p + ask_p) / 2
                    break
                elif close_p and not math.isnan(close_p) and close_p > 0:
                    price = close_p
                    break
            
            if math.isnan(price) or price <= 0:
                return None
                
            return (contract.symbol, price)
            
        except Exception as e:
            app_logger.log_debug(f"Snapshot request failed for {contract.symbol}: {e}")
            return None
        finally:
            # Properly cancel market data subscription to avoid Error 300
            if ticker:
                try:
                    # Only attempt to cancel if ticker has a valid reqId
                    if hasattr(ticker, 'reqId') and ticker.reqId is not None:
                        self.ib.cancelMktData(ticker)
                    else:
                        app_logger.log_debug(f"Ticker for {contract.symbol} has no reqId, skipping cancelMktData")
                except Exception as e:
                    # Log but don't re-raise cancellation errors
                    app_logger.log_debug(f"Error cancelling market data for {contract.symbol}: {e}")

    async def _fetch_single_historical_price(self, contract: 'Contract') -> Optional[Tuple[str, float]]:
        """
        Phase 2 helper: Fetches the last closing price for one contract from historical data.
        """
        try:
            # Request the last 1 day of data to get the most recent close
            bars = await self.ib.reqHistoricalDataAsync(
                contract,
                endDateTime="",
                durationStr="2 D",  # Request 2 days to ensure we get at least one bar
                barSizeSetting="1 day",
                whatToShow="TRADES",
                useRTH=True,
                formatDate=1
            )
            if bars:
                # Return the close of the most recent bar
                return (contract.symbol, bars[-1].close)
            return None
        except Exception as e:
            app_logger.log_warning(f"Historical data fetch failed for {contract.symbol}: {e}")
            return None

    async def get_multiple_market_prices(self, symbols: List[str], event=None) -> Dict[str, float]:
        """
        Gets market prices using a robust, two-phase concurrent strategy.
        Phase 1: Concurrent snapshot requests for all symbols during market hours.
        Phase 2: Historical data fallback for any symbols that failed Phase 1.
        """
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        if not symbols:
            return {}
        
        # Qualify all contracts first to ensure proper contract specifications
        contracts = [Stock(s, 'SMART', 'USD') for s in symbols]
        try:
            qualified_contracts = await self.ib.qualifyContractsAsync(*contracts)
            # Filter out any contracts that failed qualification
            qualified_contracts = [c for c in qualified_contracts if hasattr(c, 'conId') and c.conId]
            
            if len(qualified_contracts) != len(symbols):
                failed_symbols = [s for s in symbols if s not in [c.symbol for c in qualified_contracts]]
                app_logger.log_warning(f"Failed to qualify contracts for: {failed_symbols}", event)
                
        except Exception as e:
            app_logger.log_error(f"Failed to qualify contracts for symbols {symbols}: {e}", event)
            raise RuntimeError(f"Could not qualify contracts for: {symbols}. Cannot proceed.")

        prices: Dict[str, float] = {}
        contracts_map = {c.symbol: c for c in qualified_contracts}

        # --- Phase 1: Concurrent Snapshot Requests ---
        app_logger.log_info(f"Getting market prices using concurrent snapshot requests for {len(qualified_contracts)} symbols...")
        
        # Use gather with return_exceptions=True to handle individual failures gracefully
        snapshot_tasks = [self._fetch_single_snapshot_price(c) for c in qualified_contracts]
        snapshot_results = await asyncio.gather(*snapshot_tasks, return_exceptions=True)
        
        successful_snapshots = 0
        for i, result in enumerate(snapshot_results):
            if isinstance(result, Exception):
                app_logger.log_debug(f"Snapshot exception for {qualified_contracts[i].symbol}: {result}")
                continue
            if result:
                symbol, price = result
                prices[symbol] = price
                successful_snapshots += 1
        
        app_logger.log_info(f"Phase 1 (Snapshot) successfully got {successful_snapshots}/{len(qualified_contracts)} prices")

        # --- Phase 2: Concurrent Historical Fallback ---
        remaining_symbols = [s for s in symbols if s not in prices]
        if remaining_symbols:
            app_logger.log_info(f"Phase 2 (Historical) attempting to fetch {len(remaining_symbols)} missing prices...")
            remaining_contracts = [contracts_map[s] for s in remaining_symbols if s in contracts_map]
            
            if remaining_contracts:
                historical_tasks = [self._fetch_single_historical_price(c) for c in remaining_contracts]
                historical_results = await asyncio.gather(*historical_tasks, return_exceptions=True)

                successful_historical = 0
                for i, result in enumerate(historical_results):
                    if isinstance(result, Exception):
                        app_logger.log_debug(f"Historical exception for {remaining_contracts[i].symbol}: {result}")
                        continue
                    if result:
                        symbol, price = result
                        prices[symbol] = price
                        successful_historical += 1
                        
                app_logger.log_info(f"Phase 2 (Historical) successfully got {successful_historical}/{len(remaining_contracts)} prices")

        # --- Final Check ---
        final_missing = [s for s in symbols if s not in prices]
        if final_missing:
            app_logger.log_error(f"Could not fetch prices for: {final_missing} after all fallbacks", event)
            raise RuntimeError(f"Could not fetch price for: {final_missing} after all fallbacks.")
        
        app_logger.log_info(f"Successfully retrieved prices for all {len(prices)} symbols")
        return prices
    
    
    async def place_order(self, account_id: str, symbol: str, quantity: int, order_type: str = "MKT", event=None, 
                        time_in_force: str = "DAY", extended_hours: bool = False):
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        contract = Stock(symbol, 'SMART', 'USD')
        
        # Use the async version for consistency
        try:
            qualified_contracts = await self.ib.qualifyContractsAsync(contract)
            if not qualified_contracts:
                raise Exception(f"Could not qualify contract for {symbol}")
            contract = qualified_contracts[0]
        except Exception as e:
            app_logger.log_error(f"Failed to qualify contract for {symbol}: {e}", event)
            raise RuntimeError(f"Could not qualify contract for: {symbol}. Cannot proceed.")

        action = "BUY" if quantity > 0 else "SELL"        
        
        order = MarketOrder(action, abs(quantity))
        if extended_hours:
            order.outsideRth = True
        order.account = account_id
        
        trade = self.ib.placeOrder(contract, order)
        app_logger.log_info(f"Order placed: ID={trade.order.orderId}; {action} {abs(quantity)} shares of {symbol}", event)
        
        return trade
    
    async def cancel_all_orders(self, account_id: str, event=None) -> List[Dict]:
        """Cancel all pending orders for the given account.
        
        This method cancels all pending orders and waits up to 60 seconds for 
        confirmation from the brokerage. If any orders remain pending after 
        the timeout, an exception is raised to prevent conflicting orders 
        during rebalancing.
        
        Returns:
            List[Dict]: Details of orders that were cancelled
            
        Raises:
            Exception: If orders cannot be cancelled within 60 seconds
        """
        async with self._order_lock:
            if not await self.ensure_connected():
                raise Exception("Unable to establish IBKR connection")
            
            try:
                open_orders = self.ib.openOrders()
                cancelled_orders = []
                
                for order in open_orders:
                    if order.account == account_id:
                            
                        # Get contract symbol
                        symbol = 'Unknown'
                        if hasattr(order, 'contract') and order.contract:
                            symbol = getattr(order.contract, 'symbol', 'Unknown')
                        
                        order_details = {
                            'order_id': str(order.orderId),
                            'symbol': symbol,
                            'quantity': abs(order.totalQuantity),
                            'action': order.action,
                            'order_type': order.orderType,
                            'status': 'OpenOrder'
                        }
                        cancelled_orders.append(order_details)
                        
                        self.ib.cancelOrder(order)
                        app_logger.log_debug(f"Cancelled order {order.orderId} for {account_id}: {order.action} {abs(order.totalQuantity)} {symbol}", event)
                
                if cancelled_orders:
                    # Wait for all cancellations to be confirmed
                    await self._wait_for_orders_cancelled(account_id, max_wait_seconds=60)
                
                app_logger.log_info(f"Cancelled {len(cancelled_orders)} pending orders for account {account_id}", event)
                return cancelled_orders
                
            except Exception as e:
                app_logger.log_error(f"Failed to cancel orders for account {account_id}: {e}", event)
                raise
    
    async def _wait_for_orders_cancelled(self, account_id: str, max_wait_seconds: int = 60):
        """Wait for all pending orders to be cancelled for the account"""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            trades = self.ib.trades()
            pending_orders = [
                trade for trade in trades 
                if (trade.order.account == account_id and 
                    trade.orderStatus.status in ['PreSubmitted', 'Submitted', 'PendingSubmit'])
            ]
            
            if not pending_orders:
                app_logger.log_debug(f"All orders successfully cancelled for account {account_id}")
                return
            
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= max_wait_seconds:
                pending_ids = [trade.order.orderId for trade in pending_orders]
                error_msg = f"Timeout waiting for order cancellations for account {account_id}. Still pending: {pending_ids}"
                app_logger.log_error(error_msg)
                raise Exception(error_msg)
            
            await asyncio.sleep(10)  # Check every 10 seconds
    
    
    async def ensure_connected(self) -> bool:
        async with self._connection_lock:
            if not self.ib.isConnected():
                return await self.connect()
            
            # Simple connection check - if isConnected() returns True, trust it
            # The reqCurrentTimeAsync() was causing hangs due to event loop issues
            return True
    
    
    
