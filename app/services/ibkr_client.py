import asyncio
import random
from typing import List, Dict, Optional
from ib_async import IB, Stock, Order, MarketOrder, LimitOrder, Contract
from app.config import config
from app.logger import setup_logger

logger = setup_logger(__name__)

class IBKRClient:
    def __init__(self):
        self.ib = IB()
        self.client_id = random.randint(1000, 9999)
        self.connected = False
        self.retry_count = 0
    
    async def connect(self) -> bool:
        if self.connected:
            return True
        
        while self.retry_count < config.ibkr.max_retries:
            try:
                logger.info(f"Attempting to connect to IBKR (attempt {self.retry_count + 1})")
                
                await self.ib.connectAsync(
                    host=config.ibkr.host,
                    port=config.ibkr.port,
                    clientId=self.client_id
                )
                
                self.connected = True
                self.retry_count = 0
                logger.info(f"Connected to IBKR with client ID {self.client_id}")
                return True
                
            except Exception as e:
                self.retry_count += 1
                logger.error(f"Failed to connect to IBKR: {e}")
                
                if self.retry_count < config.ibkr.max_retries:
                    delay = config.ibkr.retry_delay * (2 ** (self.retry_count - 1))
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    
                    self.client_id = random.randint(1000, 9999)
                else:
                    logger.error("Max retries reached. Connection failed.")
                    return False
        
        return False
    
    async def disconnect(self):
        if self.connected:
            try:
                self.ib.disconnect()
                self.connected = False
                logger.info("Disconnected from IBKR")
            except Exception as e:
                logger.error(f"Error disconnecting from IBKR: {e}")
    
    async def get_account_value(self, account_id: str, tag: str = "NetLiquidation") -> float:
        if not self.connected:
            if not await self.connect():
                raise Exception("Not connected to IBKR")
        
        try:
            # Use run_in_executor to avoid blocking the event loop
            import asyncio
            loop = asyncio.get_event_loop()
            account_values = await loop.run_in_executor(None, self.ib.accountValues, account_id)
            for av in account_values:
                if av.tag == tag and av.currency == "USD":
                    return float(av.value)
            return 0.0
        except Exception as e:
            logger.error(f"Failed to get account value: {e}")
            raise
    
    async def get_positions(self, account_id: str) -> List[Dict]:
        if not self.connected:
            if not await self.connect():
                raise Exception("Not connected to IBKR")
        
        try:
            # Use run_in_executor for sync method
            import asyncio
            loop = asyncio.get_event_loop()
            positions = await loop.run_in_executor(None, self.ib.positions, account_id)
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
        if not self.connected:
            if not await self.connect():
                raise Exception("Not connected to IBKR")
        
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Use run_in_executor for sync methods that might block
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Qualify contract
            qualified_contracts = await loop.run_in_executor(None, self.ib.qualifyContracts, contract)
            if not qualified_contracts:
                raise Exception(f"Could not qualify contract for {symbol}")
            
            contract = qualified_contracts[0]
            
            # Request market data
            ticker = await loop.run_in_executor(None, self.ib.reqMktData, contract, '', False, False)
            
            # Wait for price data
            await asyncio.sleep(2)
            
            # Get the price
            price = ticker.marketPrice()
            
            # Cancel market data subscription
            await loop.run_in_executor(None, self.ib.cancelMktData, contract)
            
            # Return the price, fallback to last/close if market price not available
            if price and price > 0:
                return price
            elif ticker.last and ticker.last > 0:
                return ticker.last
            elif ticker.close and ticker.close > 0:
                return ticker.close
            else:
                raise Exception(f"No valid price data available for {symbol}")
                
        except Exception as e:
            logger.error(f"Failed to get market price for {symbol}: {e}")
            raise
    
    async def place_order(self, account_id: str, symbol: str, quantity: int, order_type: str = "MKT") -> Optional[str]:
        if not self.connected:
            if not await self.connect():
                raise Exception("Not connected to IBKR")
        
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Use run_in_executor for sync methods
            import asyncio
            loop = asyncio.get_event_loop()
            
            qualified_contracts = await loop.run_in_executor(None, self.ib.qualifyContracts, contract)
            if not qualified_contracts:
                raise Exception(f"Could not qualify contract for {symbol}")
            
            contract = qualified_contracts[0]
            
            action = "BUY" if quantity > 0 else "SELL"
            
            if order_type == "MKT":
                order = MarketOrder(action, abs(quantity))
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
            
            order.account = account_id
            
            trade = await loop.run_in_executor(None, self.ib.placeOrder, contract, order)
            logger.info(f"Placed order: {action} {abs(quantity)} shares of {symbol}")
            
            return str(trade.order.orderId)
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise
    
    async def ensure_connected(self) -> bool:
        if not self.connected:
            return await self.connect()
        
        try:
            await self.ib.reqCurrentTimeAsync()
            return True
        except:
            self.connected = False
            return await self.connect()