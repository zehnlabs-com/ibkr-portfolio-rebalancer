import asyncio
import random
from typing import List, Dict, Optional
from ib_async import IB, Stock, Order, MarketOrder, LimitOrder, Contract
from app.config import config
from app.logger import setup_logger
from app.utils.retry import retry_with_config

logger = setup_logger(__name__)

class IBKRClient:
    def __init__(self):
        self.ib = IB()
        self.ib.RequestTimeout = 10.0
        self.client_id = random.randint(1000, 9999)
        self.connected = False
        self.retry_count = 0
        
        # Add synchronization locks
        self._connection_lock = asyncio.Lock()
        self._market_data_lock = asyncio.Lock()
        self._order_lock = asyncio.Lock()
    
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
    
    async def _do_connect(self):
        """Internal connection method for retry logic"""
        # Generate new client ID for each connection attempt to avoid conflicts
        self.client_id = random.randint(1000, 9999)
        await self.ib.connectAsync(
            host=config.ibkr.host,
            port=config.ibkr.port,
            clientId=self.client_id
        )
        logger.info(f"Connected to IBKR with client ID {self.client_id}")
    
    async def disconnect(self):
        if self.ib.isConnected():
            try:
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
                    result.append({
                        'symbol': pos.contract.symbol,
                        'position': pos.position,
                        'market_value': pos.marketValue,
                        'avg_cost': pos.avgCost
                    })
            
            return result
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise
    
    async def get_market_price(self, symbol: str) -> float:
        """Get market price for a single symbol - use get_multiple_market_prices for better performance"""
        prices = await self.get_multiple_market_prices([symbol])
        return prices[symbol]
    
    async def get_multiple_market_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get market prices for multiple symbols in parallel with retry logic"""
        async with self._market_data_lock:
            if not await self.ensure_connected():
                raise Exception("Unable to establish IBKR connection")
            
            if not symbols:
                return {}
            
            try:
                return await retry_with_config(
                    self._get_market_prices_internal,
                    config.ibkr.market_data_retry,
                    "Market Data Retrieval",
                    symbols
                )
            except Exception as e:
                logger.error(f"Failed to get market prices after retries: {e}")
                raise
    
    async def _get_market_prices_internal(self, symbols: List[str]) -> Dict[str, float]:
        """Internal market data retrieval method for retry logic"""
        # Create all contracts
        contracts = [Stock(symbol, 'SMART', 'USD') for symbol in symbols]
        
        # Batch qualify all contracts at once (more efficient)
        qualified_contracts = self.ib.qualifyContracts(*contracts)
        if not qualified_contracts:
            raise Exception("No contracts could be qualified")
        
        # Create symbol to contract mapping for qualified contracts only
        qualified_symbol_map = {contract.symbol: contract for contract in qualified_contracts}
        failed_symbols = set(symbols) - set(qualified_symbol_map.keys())
        
        if failed_symbols:
            logger.warning(f"Failed to qualify contracts for symbols: {failed_symbols}")
        
        tickers = {}
        
        try:
            # Start all subscriptions simultaneously for qualified contracts
            for symbol, contract in qualified_symbol_map.items():
                ticker = self.ib.reqMktData(contract, '', False, False)
                tickers[symbol] = ticker
            
            # Wait for market data to arrive
            await asyncio.sleep(2)
            
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
                    else:
                        logger.warning(f"No valid price data available for {symbol}")
                        continue
                        
                except Exception as e:
                    logger.error(f"Failed to get price for {symbol}: {e}")
            
            # Check if we got prices for qualified symbols
            missing_symbols = set(qualified_symbol_map.keys()) - set(prices.keys())
            if missing_symbols:
                raise Exception(f"Failed to get prices for qualified symbols: {missing_symbols}")
            
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
            
            await asyncio.sleep(10)  # Check every 10 seconds
    
    async def ensure_connected(self) -> bool:
        async with self._connection_lock:
            if not self.ib.isConnected():
                return await self.connect()
            
            # Simple connection check - if isConnected() returns True, trust it
            # The reqCurrentTimeAsync() was causing hangs due to event loop issues
            return True