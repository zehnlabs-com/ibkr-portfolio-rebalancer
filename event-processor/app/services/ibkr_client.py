import asyncio
import os
import random
from typing import List, Dict, Optional, Any
from ib_async import IB, Stock, MarketOrder
from app.config import config
from app.logger import setup_logger

logger = setup_logger(__name__)
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
            logger.debug(f"Attempting to connect to IB Gateway at {config.ibkr.host}:{config.ibkr.port} with client ID {self.client_id}")
            await self.ib.connectAsync(
                host=config.ibkr.host,
                port=config.ibkr.port,
                clientId=self.client_id,
                timeout=10  # Use same timeout as old working code
            )
            logger.debug(f"Successfully connected to IB Gateway at {config.ibkr.host}:{config.ibkr.port}")
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
        """Called automatically when connection is lost"""
        logger.warning("IBKR connection lost")
        self.connected = False
        
        # Start reconnection task if not already running
        if self._reconnection_task is None or self._reconnection_task.done():
            self._reconnection_task = asyncio.create_task(self._reconnect_loop())

    def _on_connected(self):
        """Called automatically when connection is established"""
        logger.info("IBKR connection established")
        self.connected = True

    async def _reconnect_loop(self):
        """Continuously try to reconnect every 10 seconds"""
        while not self.ib.isConnected():
            try:
                logger.info("Attempting to reconnect to IBKR...")
                await self.ib.connectAsync(
                    host=config.ibkr.host,
                    port=config.ibkr.port,
                    clientId=self.client_id,
                    timeout=10
                )
                logger.info("Reconnection successful")
                break
            except Exception as e:
                logger.warning(f"Reconnection failed: {e}, retrying in 10 seconds...")
                await asyncio.sleep(10)
    
    async def disconnect(self):
        try:
            # Cancel any ongoing reconnection task
            if self._reconnection_task and not self._reconnection_task.done():
                self._reconnection_task.cancel()
                
            if self.ib.isConnected():                
                self.ib.disconnect()
                self.connected = False
                logger.debug("Disconnected from IBKR")
        except Exception as e:
            # Some ib_async internal errors during disconnect are expected
            logger.debug(f"Disconnect error (ignored): {e}")
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
            logger.error(f"Failed to get positions: {e}")
            raise
    
    
    async def get_market_price(self, symbol: str) -> float:
        """Get market price for a single symbol"""
        prices = await self.get_multiple_market_prices([symbol])
        return prices[symbol]
    
    
    async def get_multiple_market_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get market prices using a robust, qualified approach."""
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        if not symbols:
            return {}
        
        # 1. Create unqualified contract objects
        contracts = [Stock(s, 'SMART', 'USD') for s in symbols]
        
        # 2. Qualify them to get the unique conId for each
        try:
            qualified_contracts = await self.ib.qualifyContractsAsync(*contracts)
        except Exception as e:
            logger.error(f"Failed to qualify contracts for symbols {symbols}: {e}")
            raise RuntimeError(f"Could not qualify contracts for: {symbols}. Cannot proceed.")

        # 3. Request tickers using the now-qualified contracts
        tickers = await self.ib.reqTickersAsync(*qualified_contracts)
        
        prices = {t.contract.symbol: t.marketPrice() for t in tickers if t.marketPrice() > 0}
        
        missing_symbols = [s for s in symbols if s not in prices]
        if missing_symbols:
            raise RuntimeError(f"Could not fetch market price for: {missing_symbols}. Cannot proceed.")
        
        return prices
    
    
    async def place_order(self, account_id: str, symbol: str, quantity: int, order_type: str = "MKT", 
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
            logger.error(f"Failed to qualify contract for {symbol}: {e}")
            raise RuntimeError(f"Could not qualify contract for: {symbol}. Cannot proceed.")

        action = "BUY" if quantity > 0 else "SELL"        
        
        order = MarketOrder(action, abs(quantity))
        if extended_hours:
            order.outsideRth = True
        order.account = account_id
        
        trade = self.ib.placeOrder(contract, order)
        logger.info(f"Order placed: ID={trade.order.orderId}; {action} {abs(quantity)} shares of {symbol}")
        
        return trade
    
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
                        logger.debug(f"Cancelled order {order.orderId} for {account_id}: {order.action} {abs(order.totalQuantity)} {symbol}")
                
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
                logger.debug(f"All orders successfully cancelled for account {account_id}")
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
    
    
    
