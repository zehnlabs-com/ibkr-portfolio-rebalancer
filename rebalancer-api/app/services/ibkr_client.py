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
        self.ib.RequestTimeout = 10.0
        self.client_id = random.randint(1000, 9999)
        self.connected = False
        self.retry_count = 0
    
    async def connect(self) -> bool:
        if self.ib.isConnected():
            self.connected = True
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
        """Get market prices for multiple symbols in parallel (battle-tested pattern)"""
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        if not symbols:
            return {}
        
        try:
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
                        
                    # Cancel market data subscription
                    self.ib.cancelMktData(ticker.contract)
                    
                except Exception as e:
                    logger.error(f"Failed to get price for {symbol}: {e}")
                    # Still cancel the subscription even if price retrieval failed
                    try:
                        self.ib.cancelMktData(ticker.contract)
                    except:
                        pass
            
            # Check if we got prices for qualified symbols
            missing_symbols = set(qualified_symbol_map.keys()) - set(prices.keys())
            if missing_symbols:
                raise Exception(f"Failed to get prices for qualified symbols: {missing_symbols}")
            
            return prices
                
        except Exception as e:
            logger.error(f"Failed to get market prices: {e}")
            raise
    
    async def place_order(self, account_id: str, symbol: str, quantity: int, order_type: str = "MKT") -> Optional[str]:
        if not await self.ensure_connected():
            raise Exception("Unable to establish IBKR connection")
        
        try:
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
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise
    
    async def ensure_connected(self) -> bool:
        if not self.ib.isConnected():
            return await self.connect()
        
        # Simple connection check - if isConnected() returns True, trust it
        # The reqCurrentTimeAsync() was causing hangs due to event loop issues
        return True