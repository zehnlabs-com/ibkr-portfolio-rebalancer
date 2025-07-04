import asyncio
import random
from typing import List, Dict, Optional
# Removed asyncio_throttle to reduce async conflicts
from ib_async import IB, Stock, Order, MarketOrder, LimitOrder, Contract
from app.config import config
from app.logger import setup_logger
from app.utils.retry import retry_with_config

logger = setup_logger(__name__)

class IBKRClient:
    def __init__(self):
        self.ib = IB()
        self.ib.RequestTimeout = 10.0  # Match rebalancer-api timeout
        
        # Use event-processor specific client ID range to avoid conflicts
        self.client_id = random.randint(2000, 2999)
        self.connected = False
        self.retry_count = 0
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        
        # Add event handlers for connection management
        self.ib.disconnectedEvent += self._on_disconnected
        self.ib.errorEvent += self._on_error
        
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
        if self.ib.isConnected():
            self.connected = True
            return True
        
        try:
            await retry_with_config(
                self._do_connect,
                config.ibkr.connection_retry,
                "IBKR Connection"
            )
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to establish IBKR connection: {e}")
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
                await self.ib.sleep(2 ** self._reconnect_attempts)  # Exponential backoff
                if await self.connect():
                    logger.info("Successfully reconnected")
                    self._reconnect_attempts = 0
                    return
            except Exception as e:
                logger.error(f"Reconnection attempt {self._reconnect_attempts + 1} failed: {e}")
                self._reconnect_attempts += 1
    
    async def _handle_client_id_conflict(self):
        """Handle client ID conflicts by generating new ID and reconnecting"""
        logger.info("Handling client ID conflict - generating new ID")
        self.client_id = random.randint(2000, 2999)
        await self.connect()
    
    async def _do_connect(self):
        """Internal connection method for retry logic"""
        # Generate new client ID for each connection attempt to avoid conflicts
        self.client_id = random.randint(2000, 2999)
        await self.ib.connectAsync(
            host=config.ibkr.host,
            port=config.ibkr.port,
            clientId=self.client_id,
            timeout=60
        )
        logger.info(f"Connected to IBKR with client ID {self.client_id}")
    
    async def disconnect(self):
        if self.ib.isConnected():
            try:
                # Allow data to flush before disconnecting
                await self.ib.sleep(1)
                self.ib.disconnect()
                self.connected = False
                logger.info("Disconnected from IBKR")
            except Exception as e:
                logger.error(f"Error disconnecting from IBKR: {e}")
    
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
    
    async def get_positions(self, account_id: str) -> List[Dict]:
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        try:
            positions = self.ib.positions(account_id)
            result = []
            
            for pos in positions:
                if pos.position != 0:
                    # Handle cases where marketValue might not be available
                    market_value = getattr(pos, 'marketValue', None)
                    if market_value is None:
                        # Fall back to calculating market value from position and price
                        market_value = pos.position * getattr(pos, 'avgCost', 0.0)
                        logger.warning(f"marketValue not available for {pos.contract.symbol}, calculated from position * avgCost")
                    
                    result.append({
                        'symbol': pos.contract.symbol,
                        'position': pos.position,
                        'market_value': market_value,
                        'avg_cost': getattr(pos, 'avgCost', 0.0)
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
            await self.ib.sleep(0.1)  # Allow type change to propagate
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
            
            logger.info(f"Successfully retrieved prices for {len(prices)}/{len(symbols)} symbols")
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
            await self.ib.sleep(timeout)
            
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
    
    async def place_order(self, account_id: str, symbol: str, quantity: int, order_type: str = "MKT") -> Optional[str]:
        async with self._order_lock:
            if not await self.ensure_connected():
                raise Exception("Unable to establish IBKR connection")
            
            try:
                return await retry_with_config(
                    self._place_order_internal,
                    config.ibkr.order_retry,
                    "Order Placement",
                    account_id, symbol, quantity, order_type
                )
            except Exception as e:
                logger.error(f"Failed to place order after retries: {e}")
                raise
    
    async def _place_order_internal(self, account_id: str, symbol: str, quantity: int, order_type: str = "MKT") -> str:
        """Internal order placement method for retry logic"""
        contract = Stock(symbol, 'SMART', 'USD')
        
        qualified_contracts = self.ib.qualifyContracts(contract)
        if not qualified_contracts:
            raise Exception(f"Could not qualify contract for {symbol}")
        
        contract = qualified_contracts[0]
        
        action = "BUY" if quantity > 0 else "SELL"
        
        if order_type == "MKT":
            order = MarketOrder(action, abs(quantity))
        elif order_type == "MOC":
            order = Order()
            order.orderType = "MOC"
            order.action = action
            order.totalQuantity = abs(quantity)
        else:
            raise ValueError(f"Unsupported order type: {order_type}")
        
        order.account = account_id
        
        trade = self.ib.placeOrder(contract, order)
        logger.info(f"Placed order: {action} {abs(quantity)} shares of {symbol}")
        
        return str(trade.order.orderId)
    
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
            
            await self.ib.sleep(10)  # Check every 10 seconds
    
    async def ensure_connected(self) -> bool:
        async with self._connection_lock:
            if not self.ib.isConnected():
                return await self.connect()
            
            # Simple connection check - if isConnected() returns True, trust it
            # The reqCurrentTimeAsync() was causing hangs due to event loop issues
            return True
    
    async def get_historical_price(self, symbol: str, include_extended_hours: bool = True) -> Optional[float]:
        """Get most recent price from historical data for a single symbol"""
        prices = await self._get_historical_prices_batch([symbol], include_extended_hours)
        return prices.get(symbol)
    
    async def _get_historical_prices_batch(self, symbols: List[str], include_extended_hours: bool = True) -> Dict[str, float]:
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
                    await self.ib.sleep(self._min_request_interval - time_since_last)
                
                self._last_historical_request = loop.time()
                price = await self._get_single_historical_price(symbol, include_extended_hours)
                if price:
                    prices[symbol] = price
            except Exception as e:
                logger.error(f"Failed to get historical price for {symbol}: {e}")
        
        return prices
    
    async def _get_single_historical_price(self, symbol: str, include_extended_hours: bool = True) -> Optional[float]:
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
                useRTH=not include_extended_hours,  # False = include extended hours
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