# app/services/ibkr_client.py
from ib_insync import IB, Stock, MarketOrder
from app.config import Settings
import asyncio
import random
from loguru import logger
from typing import Dict

class IBKRClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.ib = IB()
        self._connected = False
        # Random client ID to avoid conflicts
        self.client_id = random.randint(10, 100)
    
    async def connect(self, max_retries: int = 3):
        """Connect to IBKR using proper async method"""
        if self._connected and self.ib.isConnected():
            return
            
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to IBKR (attempt {attempt + 1}) - Client ID: {self.client_id}")
                
                await self.ib.connectAsync(
                    host=self.settings.ibkr_host,
                    port=self.settings.ibkr_port,
                    clientId=self.client_id,
                    timeout=15
                )
                
                if self.ib.isConnected():
                    self._connected = True
                    logger.info("Successfully connected to IBKR")
                    return
                    
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
                
                try:
                    self.ib.disconnect()
                except:
                    pass
                
                if attempt < max_retries - 1:
                    self.client_id = random.randint(10, 100)
                    await asyncio.sleep(5)
                else:
                    logger.error("Failed to connect after all retries")
                    raise Exception(f"Unable to connect to IBKR after {max_retries} attempts. Please check IBKR Gateway is running and accessible.")
    
    def disconnect(self):
        """Disconnect from IBKR"""
        if self._connected:
            try:
                self.ib.disconnect()
                self._connected = False
                logger.info("Disconnected from IBKR")
            except Exception as e:
                logger.warning(f"Error during disconnect: {str(e)}")
    
    async def get_account_value(self) -> float:
        """Get total account value"""
        try:
            if not self._connected:
                await self.connect()
            
            account_summary = self.ib.accountSummary()
            
            # Find NetLiquidation value
            for item in account_summary:
                if item.tag == 'NetLiquidation' and item.value:
                    try:
                        value = float(item.value)
                        logger.info(f"Account value: ${value:,.2f}")
                        return value
                    except (ValueError, TypeError):
                        continue
            
            # If we get here, no valid account value was found
            raise Exception("Unable to retrieve account value from IBKR. No NetLiquidation data available.")
            
        except Exception as e:
            logger.error(f"Error getting account value: {str(e)}")
            raise Exception(f"Failed to get account value: {str(e)}")
    
    async def get_positions(self) -> Dict:
        """Get current positions"""
        try:
            if not self._connected:
                await self.connect()
            
            positions = self.ib.positions()
            position_dict = {}
            
            for position in positions:
                if position.position != 0:
                    symbol = position.contract.symbol
                    
                    # Get current market price
                    try:
                        market_price = await self.get_current_price(symbol)
                    except Exception as e:
                        logger.error(f"Failed to get price for {symbol}: {str(e)}")
                        raise Exception(f"Unable to get current price for {symbol}: {str(e)}")
                    
                    market_value = position.position * market_price
                    
                    position_dict[symbol] = {
                        'shares': int(position.position),
                        'avg_cost': float(position.avgCost) if position.avgCost else 0.0,
                        'market_value': market_value,
                        'market_price': market_price
                    }
            
            return position_dict
            
        except Exception as e:
            logger.error(f"Error getting positions: {str(e)}")
            raise Exception(f"Failed to get positions: {str(e)}")
    
    async def get_current_price(self, symbol: str) -> float:
        """Get current market price"""
        try:
            if not self._connected:
                await self.connect()
            
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Use async market data request
            self.ib.reqMktData(contract, '', False, False)
            await asyncio.sleep(2)  # Wait for data
            
            ticker = self.ib.ticker(contract)
            
            # Try to get price
            price = None
            if ticker.marketPrice() and ticker.marketPrice() > 0:
                price = ticker.marketPrice()
            elif ticker.close and ticker.close > 0:
                price = ticker.close
            elif ticker.last and ticker.last > 0:
                price = ticker.last
            
            # Cancel to clean up
            self.ib.cancelMktData(contract)
            
            if price and price > 0:
                logger.info(f"Price for {symbol}: ${price:.2f}")
                return float(price)
            else:
                raise Exception(f"No valid price data available for {symbol}")
                
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {str(e)}")
            raise Exception(f"Failed to get current price for {symbol}: {str(e)}")
    
    async def place_order(self, symbol: str, quantity: int, action: str):
        """Place market order"""
        try:
            if not self._connected:
                await self.connect()
            
            contract = Stock(symbol, 'SMART', 'USD')
            order = MarketOrder(action.upper(), quantity)
            
            trade = self.ib.placeOrder(contract, order)
            await asyncio.sleep(1)  # Brief wait
            
            logger.info(f"Order placed: {action.upper()} {quantity} {symbol}")
            return trade
            
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            raise Exception(f"Failed to place order for {symbol}: {str(e)}")