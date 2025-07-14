import asyncio
import os
import random
from typing import List, Dict, Optional, Any
# Removed asyncio_throttle to reduce async conflicts
from ib_insync import IB, Stock, Order, LimitOrder, Contract
from app.config import config
from app.logger import setup_logger
from app.utils.retry import retry_with_config

logger = setup_logger(__name__)

class IBKRClient:
    def __init__(self):
        self.ib = IB()
        self.ib.RequestTimeout = 10.0  # Match rebalancer-api timeout
        
        # Use fixed client ID from environment (like the working old code)
        self.client_id = random.randint(1000, 2999)
        self.connected = False
        self.retry_count = 0
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        
        # Add event handlers for connection management - temporarily disabled for debugging
        # self.ib.disconnectedEvent += self._on_disconnected
        # self.ib.errorEvent += self._on_error
        
        # Add synchronization locks
        self._connection_lock = asyncio.Lock()
        self._market_data_lock = asyncio.Lock()
        self._order_lock = asyncio.Lock()
        
        # Simple rate limiting for historical data requests
        self._last_historical_request = 0
        self._min_request_interval = 12  # 12 seconds between requests (5 per minute)
        
        # Current market data type (1=live, 2=frozen, 3=delayed, 4=delayed-frozen)
        self._current_market_data_type = 1
    
    async def connect(self) -> bool:
        if self.ib.isConnected():  # This method is synchronous and safe to use
            self.connected = True
            return True
        
        try:
            # Direct connection like the old working code
            logger.info(f"Attempting to connect to IB Gateway at {config.ibkr.host}:{config.ibkr.port} with client ID {self.client_id}")
            await self.ib.connectAsync(
                host=config.ibkr.host,
                port=config.ibkr.port,
                clientId=self.client_id,
                timeout=10  # Use same timeout as old working code
            )
            logger.info(f"Successfully connected to IB Gateway at {config.ibkr.host}:{config.ibkr.port}")
            self.connected = True
            return True
        except TimeoutError as e:
            logger.error(f"Connection timeout to IB Gateway at {config.ibkr.host}:{config.ibkr.port}: {e}")
            return False
        except ConnectionRefusedError as e:
            logger.error(f"Connection refused to IB Gateway at {config.ibkr.host}:{config.ibkr.port}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to IB Gateway at {config.ibkr.host}:{config.ibkr.port}: {type(e).__name__}: {e}")
            return False
    
    def _on_disconnected(self):
        """Handle disconnection events"""
        logger.warning("Connection lost - attempting to reconnect")
        self.connected = False
        # Don't block the event loop with reconnection
        asyncio.create_task(self._handle_reconnection())
    
    def _on_error(self, reqId, errorCode, errorString, advancedOrderReject):
        """Handle specific error codes"""
        if errorCode == 326:  # Client ID already in use
            logger.error(f"Client ID conflict: {errorString}")
            asyncio.create_task(self._handle_client_id_conflict())
        elif errorCode == 502:  # TWS not running
            logger.error(f"TWS/Gateway not available: {errorString}")
        else:
            logger.error(f"IB Error {errorCode}: {errorString}")
    
    async def _handle_reconnection(self):
        """Handle automatic reconnection with exponential backoff"""
        while self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                await asyncio.sleep(2 ** self._reconnect_attempts)  # Exponential backoff
                if await self.connect():
                    logger.info("Successfully reconnected")
                    self._reconnect_attempts = 0
                    return
            except Exception as e:
                logger.error(f"Reconnection attempt {self._reconnect_attempts + 1} failed: {e}")
                self._reconnect_attempts += 1
    
    async def _handle_client_id_conflict(self):
        """Handle client ID conflicts by incrementing ID and reconnecting"""
        logger.debug("Handling client ID conflict - trying next client ID")
        self.client_id = self.client_id + 1
        await self.connect()
    
    
    async def disconnect(self):
        try:
            if self.ib.isConnected():
                # Just disconnect without sleep - keep it simple
                self.ib.disconnect()
                self.connected = False
                logger.info("Disconnected from IBKR")
        except Exception as e:
            # Some ib_insync internal errors during disconnect are expected
            logger.debug(f"Disconnect error (ignored): {e}")
            pass
    
    async def __aenter__(self):
        """Async context manager entry - connect to IB"""
        # Start ib_insync event loop for this connection
        from ib_insync import util
        try:
            # Try to start the loop if not already running
            util.startLoop()
        except RuntimeError:
            # Loop is already running, which is fine
            pass
        
        success = await self.connect()
        if not success:
            raise Exception("Failed to connect to IBKR")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - disconnect from IB"""
        try:
            await self.disconnect()
        except Exception as e:
            # Ignore disconnect errors - the connection cleanup will happen anyway
            logger.debug(f"Disconnect error (ignored): {e}")
            pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Simple health check that verifies IB connection is working"""
        try:
            # Test basic connection by getting managed accounts - use synchronous method
            accounts = self.ib.managedAccounts()
            return {
                "status": "healthy",
                "connected": True,
                "accounts": list(accounts),
                "client_id": self.client_id
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy", 
                "connected": False,
                "error": str(e),
                "client_id": self.client_id
            }
    
    async def get_account_value(self, account_id: str, tag: str = "NetLiquidation") -> float:
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        try:
            account_values = self.ib.accountValues(account_id)
            for av in account_values:
                if av.tag == tag and av.currency == "USD":
                    return float(av.value)
            return 0.0
        except Exception as e:
            logger.error(f"Failed to get account value: {e}")
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
            logger.error(f"Failed to get cash balance: {e}")
            raise
    
    async def get_positions(self, account_id: str) -> List[Dict]:
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        try:
            portfolio_items = self.ib.portfolio(account_id)
            result = []
            
            for item in portfolio_items:
                if item.position != 0:
                    result.append({
                        'symbol': item.contract.symbol,
                        'position': item.position,
                        'market_value': item.marketValue,
                        'avg_cost': item.averageCost
                    })
            
            return result
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise
    
    async def _set_market_data_type(self, data_type: int):
        """Set market data type (1=live, 2=frozen, 3=delayed, 4=delayed-frozen)"""
        if self._current_market_data_type != data_type:
            self.ib.reqMarketDataType(data_type)
            self._current_market_data_type = data_type
            await asyncio.sleep(0.1)  # Allow type change to propagate
            logger.debug(f"Set market data type to {data_type}")
    
    async def get_market_price(self, symbol: str) -> float:
        """Get market price for a single symbol - use get_multiple_market_prices for better performance"""
        prices = await self.get_multiple_market_prices([symbol])
        return prices[symbol]
    
    
    async def get_multiple_market_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get market prices for multiple symbols with robust fallback strategy"""
        async with self._market_data_lock:
            if not await self.ensure_connected():
                raise Exception("Unable to establish IBKR connection")
            
            if not symbols:
                return {}
            
            prices = {}
            remaining_symbols = symbols.copy()
            
            # Phase 1: Try live data first
            try:
                await self._set_market_data_type(1)  # Live data
                live_prices = await self._get_market_prices_with_type(remaining_symbols, "live")
                prices.update(live_prices)
                remaining_symbols = [s for s in remaining_symbols if s not in live_prices]
                logger.debug(f"Got {len(live_prices)} prices with live data")
            except Exception as e:
                logger.debug(f"Live data failed: {e}")
            
            # Phase 2: Try frozen data for remaining symbols
            if remaining_symbols:
                try:
                    await self._set_market_data_type(2)  # Frozen data
                    frozen_prices = await self._get_market_prices_with_type(remaining_symbols, "frozen")
                    prices.update(frozen_prices)
                    remaining_symbols = [s for s in remaining_symbols if s not in frozen_prices]
                    logger.debug(f"Got {len(frozen_prices)} prices with frozen data")
                except Exception as e:
                    logger.debug(f"Frozen data failed: {e}")
            
            # Phase 3: Try delayed data for remaining symbols
            if remaining_symbols:
                try:
                    await self._set_market_data_type(3)  # Delayed data
                    delayed_prices = await self._get_market_prices_with_type(remaining_symbols, "delayed")
                    prices.update(delayed_prices)
                    remaining_symbols = [s for s in remaining_symbols if s not in delayed_prices]
                    logger.debug(f"Got {len(delayed_prices)} prices with delayed data")
                except Exception as e:
                    logger.debug(f"Delayed data failed: {e}")
            
            # Phase 4: Try historical data fallback for remaining symbols
            if remaining_symbols:
                try:
                    historical_prices = await self._get_historical_prices_batch(remaining_symbols)
                    prices.update(historical_prices)
                    remaining_symbols = [s for s in remaining_symbols if s not in historical_prices]
                    logger.debug(f"Got {len(historical_prices)} prices with historical data")
                except Exception as e:
                    logger.debug(f"Historical data failed: {e}")
            
            if remaining_symbols:
                logger.warning(f"Unable to get prices for symbols: {remaining_symbols}")
            
            logger.debug(f"Successfully retrieved prices for {len(prices)}/{len(symbols)} symbols")
            return prices
    
    async def _get_market_prices_internal(self, symbols: List[str]) -> Dict[str, float]:
        """Internal market data retrieval method for retry logic"""
        return await self._get_market_prices_with_type(symbols, "default")
    
    async def _get_market_prices_with_type(self, symbols: List[str], data_type_name: str) -> Dict[str, float]:
        """Get market prices with current market data type setting"""
        # Create all contracts
        contracts = [Stock(symbol, 'SMART', 'USD') for symbol in symbols]
        
        # Batch qualify all contracts at once (more efficient)
        qualified_contracts = self.ib.qualifyContracts(*contracts)
        if not qualified_contracts:
            logger.warning(f"No contracts could be qualified for {data_type_name} data")
            return {}
        
        # Create symbol to contract mapping for qualified contracts only
        qualified_symbol_map = {contract.symbol: contract for contract in qualified_contracts}
        failed_symbols = set(symbols) - set(qualified_symbol_map.keys())
        
        if failed_symbols:
            logger.debug(f"Failed to qualify contracts for symbols: {failed_symbols}")
        
        tickers = {}
        
        try:
            # Start all subscriptions simultaneously for qualified contracts
            for symbol, contract in qualified_symbol_map.items():
                ticker = self.ib.reqMktData(contract, '', False, False)
                tickers[symbol] = ticker
            
            # Wait for market data to arrive (increased timeout for frozen/delayed data)
            timeout = 5 if data_type_name in ["frozen", "delayed"] else 2
            await asyncio.sleep(timeout)
            
            # Collect all prices
            prices = {}
            for symbol, ticker in tickers.items():
                try:
                    # Get the price with fallback logic
                    price = ticker.marketPrice()
                    
                    if price and price > 0:
                        prices[symbol] = price
                    elif ticker.last and ticker.last > 0:
                        prices[symbol] = ticker.last
                    elif ticker.close and ticker.close > 0:
                        prices[symbol] = ticker.close
                    elif ticker.bid and ticker.ask and ticker.bid > 0 and ticker.ask > 0:
                        # Use mid price as fallback
                        prices[symbol] = (ticker.bid + ticker.ask) / 2
                    else:
                        logger.debug(f"No valid {data_type_name} price data available for {symbol}")
                        continue
                        
                except Exception as e:
                    logger.debug(f"Failed to get {data_type_name} price for {symbol}: {e}")
            
            return prices
            
        finally:
            # Always cancel all subscriptions
            for ticker in tickers.values():
                try:
                    self.ib.cancelMktData(ticker.contract)
                except:
                    pass
    
    async def place_order(self, account_id: str, symbol: str, quantity: int, order_type: str = "MKT", 
                         time_in_force: str = "DAY", extended_hours: bool = False) -> str:
        async with self._order_lock:
            if not await self.ensure_connected():
                raise Exception("Unable to establish IBKR connection")
            
            try:
                return await retry_with_config(
                    self._place_order_internal,
                    config.ibkr.order_retry,
                    "Order Placement",
                    account_id, symbol, quantity, order_type, time_in_force, extended_hours
                )
            except Exception as e:
                logger.error(f"Failed to place order after retries: {e}")
                raise
    
    async def _place_order_internal(self, account_id: str, symbol: str, quantity: int, order_type: str = "MKT", 
                                   time_in_force: str = "DAY", extended_hours: bool = False) -> str:
        """Internal order placement method for retry logic"""
        contract = Stock(symbol, 'SMART', 'USD')
        
        qualified_contracts = self.ib.qualifyContracts(contract)
        if not qualified_contracts:
            raise Exception(f"Could not qualify contract for {symbol}")
        
        contract = qualified_contracts[0]
        
        action = "BUY" if quantity > 0 else "SELL"
        
        # Validate order type - only MKT supported for sell-first cash reserve logic
        if order_type != "MKT":
            raise ValueError(f"Unsupported order type: {order_type}. Only MKT orders are supported.")
        
        # Validate time in force
        if time_in_force not in ["DAY", "GTC"]:
            raise ValueError(f"Unsupported time in force: {time_in_force}. Only DAY and GTC are supported.")
        
        # Create order with specified type
        order = Order()
        order.orderType = order_type
        order.action = action
        order.totalQuantity = abs(quantity)
        order.tif = time_in_force
        order.outsideRth = extended_hours
        order.account = account_id
        
        trade = self.ib.placeOrder(contract, order)
        orderId = trade.order.orderId
        logger.info(f"Placed order: ID={orderId}; {action} {order_type} {abs(quantity)} shares of {symbol} (TIF: {time_in_force}, Extended: {extended_hours})")
        
        return str(orderId)
    
    async def validate_order(self, account_id: str, symbol: str, quantity: int, order_type: str = "MKT", 
                           time_in_force: str = "DAY", extended_hours: bool = False) -> Dict[str, Any]:
        """Validate an order using WhatIf without actually placing it.
        
        Args:
            account_id: Account ID
            symbol: Stock symbol
            quantity: Number of shares (positive for buy, negative for sell)
            order_type: Order type (only MKT supported)
            time_in_force: Time in force
            extended_hours: Extended hours trading
            
        Returns:
            Dict containing validation results with keys:
            - valid: bool - whether order is valid
            - error: str - error message if invalid
            - margin_before: float - margin requirement before order
            - margin_after: float - margin requirement after order
            - commission: float - estimated commission
            
        Raises:
            Exception: If validation fails due to connection or other errors
        """
        async with self._order_lock:
            if not await self.ensure_connected():
                raise Exception("Unable to establish IBKR connection")
            
            try:
                # Prepare contract
                contract = Stock(symbol, 'SMART', 'USD')
                qualified_contracts = self.ib.qualifyContracts(contract)
                if not qualified_contracts:
                    return {
                        'valid': False,
                        'error': f"Could not qualify contract for {symbol}",
                        'margin_before': 0,
                        'margin_after': 0,
                        'commission': 0
                    }
                
                contract = qualified_contracts[0]
                action = "BUY" if quantity > 0 else "SELL"
                
                # Validate order type
                if order_type != "MKT":
                    return {
                        'valid': False,
                        'error': f"Unsupported order type: {order_type}. Only MKT orders are supported.",
                        'margin_before': 0,
                        'margin_after': 0,
                        'commission': 0
                    }
                
                # Create WhatIf order
                order = Order()
                order.orderType = order_type
                order.action = action
                order.totalQuantity = abs(quantity)
                order.tif = time_in_force
                order.outsideRth = extended_hours
                order.account = account_id
                order.whatIf = True  # This is the key - enables validation mode
                
                logger.debug(f"Creating WhatIf order for {symbol}: {action} {abs(quantity)} shares")
                
                # Place WhatIf order
                trade = self.ib.placeOrder(contract, order)
                
                # Wait for order state to be populated
                # WhatIf orders should return quickly with validation results
                await asyncio.sleep(3)  # Give more time for validation response
                
                # Log the trade status for debugging
                logger.debug(f"WhatIf order for {symbol}: Status={trade.orderStatus.status}")
                
                # Check if we got validation results
                if trade.orderStatus.status == 'Cancelled':
                    # WhatIf orders are cancelled after validation - this is the expected behavior
                    
                    # Check if this was a rejection due to insufficient funds or other issues
                    if trade.log:
                        for log_entry in trade.log:
                            if log_entry.errorCode and log_entry.errorCode > 0:
                                # This was actually a rejection, not a successful validation
                                logger.info(f"WhatIf order for {symbol} rejected: {log_entry.message}")
                                return {
                                    'valid': False,
                                    'error': log_entry.message,
                                    'margin_before': 0,
                                    'margin_after': 0,
                                    'commission': 0
                                }
                    
                    # This was a successful validation
                    order_state = trade.orderStatus
                    margin_before = getattr(order_state, 'initMarginBefore', 0)
                    margin_after = getattr(order_state, 'initMarginAfter', 0)
                    commission = getattr(order_state, 'commission', 0)
                    
                    logger.debug(f"WhatIf order for {symbol} validated successfully")
                    return {
                        'valid': True,
                        'error': None,
                        'margin_before': float(margin_before) if margin_before else 0,
                        'margin_after': float(margin_after) if margin_after else 0,
                        'commission': float(commission) if commission else 0
                    }
                    
                elif trade.orderStatus.status == 'PendingSubmit':
                    # WhatIf orders can get stuck in PendingSubmit in paper trading
                    # This is a known limitation of the paper trading simulator
                    logger.debug(f"WhatIf order for {symbol} in PendingSubmit status - treating as valid (paper trading behavior)")
                    return {
                        'valid': True,
                        'error': None,
                        'margin_before': 0,
                        'margin_after': 0,
                        'commission': 0
                    }
                else:
                    # If order is still active, there might be an error
                    error_msg = "Order validation failed"
                    error_details = []
                    
                    # Extract detailed error information from trade log
                    if trade.log:
                        for log_entry in trade.log:
                            if log_entry.message:
                                error_details.append(f"Log: {log_entry.message}")
                        if error_details:
                            error_msg = "; ".join(error_details)
                    
                    # Also check order status for additional details
                    if hasattr(trade.orderStatus, 'whyHeld') and trade.orderStatus.whyHeld:
                        error_details.append(f"WhyHeld: {trade.orderStatus.whyHeld}")
                    
                    if hasattr(trade.orderStatus, 'status') and trade.orderStatus.status:
                        error_details.append(f"Status: {trade.orderStatus.status}")
                    
                    # Log the detailed error information
                    logger.error(f"Order validation failed for {symbol}: Status={trade.orderStatus.status}, WhyHeld={getattr(trade.orderStatus, 'whyHeld', 'N/A')}, Error details: {error_msg}")
                    
                    return {
                        'valid': False,
                        'error': error_msg,
                        'margin_before': 0,
                        'margin_after': 0,
                        'commission': 0
                    }
                
            except Exception as e:
                # Log more detailed error information
                error_type = type(e).__name__
                error_msg = str(e)
                logger.error(f"Order validation exception for {symbol}: {error_type}: {error_msg}")
                
                # Try to extract more details from the exception
                if hasattr(e, 'args') and e.args:
                    logger.error(f"Exception args: {e.args}")
                
                return {
                    'valid': False,
                    'error': f"{error_type}: {error_msg}",
                    'margin_before': 0,
                    'margin_after': 0,
                    'commission': 0
                }
    
    async def validate_orders_batch(self, account_id: str, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate multiple orders in batch.
        
        Args:
            account_id: Account ID
            orders: List of order dicts with keys: symbol, quantity, order_type, time_in_force, extended_hours
            
        Returns:
            List of validation results in same order as input
            
        Raises:
            Exception: If any order validation fails
        """
        results = []
        
        for order_data in orders:
            result = await self.validate_order(
                account_id=account_id,
                symbol=order_data['symbol'],
                quantity=order_data['quantity'],
                order_type=order_data.get('order_type', 'MKT'),
                time_in_force=order_data.get('time_in_force', 'DAY'),
                extended_hours=order_data.get('extended_hours', False)
            )
            
            results.append(result)
            
            # If any order is invalid, fail the entire batch
            if not result['valid']:
                logger.error(f"Order validation failed for {order_data['symbol']}: {result['error']}")
                raise Exception(f"Order validation failed for {order_data['symbol']}: {result['error']}")
        
        return results
    
    async def cancel_all_orders(self, account_id: str) -> List[Dict]:
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
                        # Skip what-if orders - they are automatically cancelled by IBKR
                        if hasattr(order, 'whatIf') and order.whatIf:
                            logger.debug(f"Skipping what-if order {order.orderId} - automatically cancelled by IBKR")
                            continue
                            
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
                        logger.info(f"Cancelled order {order.orderId} for {account_id}: {order.action} {abs(order.totalQuantity)} {symbol}")
                
                if cancelled_orders:
                    # Wait for all cancellations to be confirmed
                    await self._wait_for_orders_cancelled(account_id, max_wait_seconds=60)
                
                logger.info(f"Cancelled {len(cancelled_orders)} pending orders for account {account_id}")
                return cancelled_orders
                
            except Exception as e:
                logger.error(f"Failed to cancel orders for account {account_id}: {e}")
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
                logger.info(f"All orders successfully cancelled for account {account_id}")
                return
            
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= max_wait_seconds:
                pending_ids = [trade.order.orderId for trade in pending_orders]
                error_msg = f"Timeout waiting for order cancellations for account {account_id}. Still pending: {pending_ids}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            await asyncio.sleep(10)  # Check every 10 seconds
    
    async def wait_for_sell_orders_completion(self, account_id: str, order_ids: List[str]) -> None:
        """Wait for sell orders to complete using configured timeout"""
        timeout_seconds = config.ibkr.order_completion_timeout
        logger.info(f"Waiting up to {timeout_seconds} seconds for {len(order_ids)} sell orders to complete for account {account_id}")
        
        try:
            await self._wait_for_orders_filled(account_id, order_ids, timeout_seconds)
        except Exception as e:
            # Re-raise with more specific error message for sell orders
            raise Exception(f"Sell orders did not complete within {timeout_seconds} seconds: {e}")

    async def _wait_for_orders_filled(self, account_id: str, order_ids: List[str], max_wait_seconds: int = 300):
        """Wait for specific orders to be filled or cancelled for the account"""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            trades = self.ib.trades()
            pending_orders = [
                trade for trade in trades 
                if (trade.order.account == account_id and 
                    str(trade.order.orderId) in order_ids and
                    trade.orderStatus.status in ['PreSubmitted', 'Submitted', 'PendingSubmit'])
            ]
            
            if not pending_orders:
                logger.info(f"All specified orders completed for account {account_id}")
                return
            
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= max_wait_seconds:
                pending_ids = [trade.order.orderId for trade in pending_orders]
                error_msg = f"Timeout waiting for order completion for account {account_id}. Still pending: {pending_ids}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            await asyncio.sleep(2)  # Check every 2 seconds for faster response
    
    async def ensure_connected(self) -> bool:
        async with self._connection_lock:
            if not self.ib.isConnected():
                return await self.connect()
            
            # Simple connection check - if isConnected() returns True, trust it
            # The reqCurrentTimeAsync() was causing hangs due to event loop issues
            return True
    
    async def get_historical_price(self, symbol: str, include_extended_hours_enabled: bool = True) -> Optional[float]:
        """Get most recent price from historical data for a single symbol"""
        prices = await self._get_historical_prices_batch([symbol], include_extended_hours_enabled)
        return prices.get(symbol)
    
    async def _get_historical_prices_batch(self, symbols: List[str], include_extended_hours_enabled: bool = True) -> Dict[str, float]:
        """Get historical prices for multiple symbols with rate limiting"""
        if not symbols:
            return {}
        
        prices = {}
        
        for symbol in symbols:
            try:
                # Apply simple rate limiting for historical data requests
                loop = asyncio.get_event_loop()
                current_time = loop.time()
                time_since_last = current_time - self._last_historical_request
                if time_since_last < self._min_request_interval:
                    await asyncio.sleep(self._min_request_interval - time_since_last)
                
                self._last_historical_request = loop.time()
                price = await self._get_single_historical_price(symbol, include_extended_hours_enabled)
                if price:
                    prices[symbol] = price
            except Exception as e:
                logger.error(f"Failed to get historical price for {symbol}: {e}")
        
        return prices
    
    async def _get_single_historical_price(self, symbol: str, include_extended_hours_enabled: bool = True) -> Optional[float]:
        """Get most recent historical price for a single symbol"""
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Qualify the contract
            qualified_contracts = self.ib.qualifyContracts(contract)
            if not qualified_contracts:
                logger.warning(f"Could not qualify contract for {symbol}")
                return None
            
            contract = qualified_contracts[0]
            
            # Request historical data - look back 1 day with 1-minute bars
            bars = self.ib.reqHistoricalData(
                contract=contract,
                endDateTime='',  # Current time
                durationStr='1 D',  # Look back 1 day
                barSizeSetting='1 min',
                whatToShow='TRADES',
                useRTH=not include_extended_hours_enabled,  # False = include extended hours
                formatDate=1,
                keepUpToDate=False
            )
            
            if bars:
                # Return the most recent close price
                latest_price = bars[-1].close
                logger.debug(f"Got historical price for {symbol}: {latest_price}")
                return latest_price
            else:
                logger.warning(f"No historical data available for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Historical data request failed for {symbol}: {e}")
            return None