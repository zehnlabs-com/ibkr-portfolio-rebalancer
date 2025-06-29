# app/services/ibkr_service.py
import asyncio
import nest_asyncio
from contextlib import asynccontextmanager
from ib_async import IB, Stock, MarketOrder
from app.config import Settings
from loguru import logger
from typing import Dict, Optional
import random

# Apply nest_asyncio patch - this is the community standard approach
nest_asyncio.apply()

class IBKRService:
    """Singleton IBKR service - community standard pattern"""
    
    _instance: Optional['IBKRService'] = None
    _initialized: bool = False
    
    def __new__(cls, settings: Settings = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, settings: Settings = None):
        if not self._initialized:
            self.settings = settings or Settings()
            self.ib = IB()
            self._connection_task: Optional[asyncio.Task] = None
            self._shutdown_event = asyncio.Event()
            self.client_id = random.randint(10, 100)
            IBKRService._initialized = True
    
    async def start_service(self):
        """Start the IBKR connection service"""
        logger.info("Starting IBKR service...")
        self._shutdown_event.clear()
        self._connection_task = asyncio.create_task(self._maintain_connection())
    
    async def stop_service(self):
        """Stop the IBKR connection service"""
        logger.info("Stopping IBKR service...")
        self._shutdown_event.set()
        
        if self._connection_task:
            self._connection_task.cancel()
            try:
                await self._connection_task
            except asyncio.CancelledError:
                pass
        
        if self.ib.isConnected():
            self.ib.disconnect()
            logger.info("Disconnected from IBKR")
    
    async def _maintain_connection(self):
        """Background task to maintain IBKR connection - community pattern"""
        while not self._shutdown_event.is_set():
            try:
                if not self.ib.isConnected():
                    logger.info(f"Attempting to connect to IBKR - Client ID: {self.client_id}")
                    # Use the community standard connectAsync pattern
                    await self.ib.connectAsync(
                        host=self.settings.ibkr_host,
                        port=self.settings.ibkr_port,
                        clientId=self.client_id,
                        timeout=15
                    )
                    if self.ib.isConnected():
                        logger.info("Successfully connected to IBKR")
                    else:
                        logger.warning("Connection attempt failed")
                        self.client_id = random.randint(10, 100)
                
                # Wait before next check
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=30)
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    continue  # Normal operation, check connection again
                    
            except Exception as e:
                logger.warning(f"Connection error: {str(e)}")
                self.client_id = random.randint(10, 100)
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=10)
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    continue  # Retry connection
    
    def is_connected(self) -> bool:
        """Check if connected to IBKR"""
        return self.ib.isConnected()
    
    def _ensure_connected(self):
        """Simple connection check - community pattern"""
        if not self.is_connected():
            raise Exception("IBKR connection not available. Check /api/v1/connection/status for details.")
    
    async def get_account_value(self) -> float:
        """Get total account value - simplified community approach"""
        self._ensure_connected()
        
        try:
            # Use specific account if configured
            account_summary = self.ib.accountSummary(account=self.settings.ibkr_account_id)
            
            # Find NetLiquidation value
            for item in account_summary:
                if item.tag == 'NetLiquidation' and item.value:
                    try:
                        value = float(item.value)
                        logger.info(f"Account value: ${value:,.2f}")
                        return value
                    except (ValueError, TypeError):
                        continue
            
            raise Exception("Unable to retrieve account value from IBKR. No NetLiquidation data available.")
            
        except Exception as e:
            logger.error(f"Error getting account value: {str(e)}")
            raise Exception(f"Failed to get account value: {str(e)}")
    
    async def get_positions(self) -> Dict:
        """Get current positions - simplified community approach"""
        self._ensure_connected()
        
        try:
            positions = self.ib.positions(account=self.settings.ibkr_account_id)
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
        """Get current market price - community standard approach"""
        self._ensure_connected()
        
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Qualify the contract to populate conId
            qualified_contracts = await self.ib.qualifyContractsAsync(contract)
            if not qualified_contracts:
                raise Exception(f"Could not qualify contract for {symbol}")
            
            qualified_contract = qualified_contracts[0]
            
            # Simple market data request - nest_asyncio handles the complexity
            self.ib.reqMktData(qualified_contract, '', False, False)
            await asyncio.sleep(2)  # Standard wait time used by community
            
            ticker = self.ib.ticker(qualified_contract)
            
            # Try to get price - standard approach
            price = None
            if ticker.marketPrice() and ticker.marketPrice() > 0:
                price = ticker.marketPrice()
            elif ticker.close and ticker.close > 0:
                price = ticker.close
            elif ticker.last and ticker.last > 0:
                price = ticker.last
            
            # Clean up
            self.ib.cancelMktData(qualified_contract)
            
            if price and price > 0:
                logger.info(f"Price for {symbol}: ${price:.2f}")
                return float(price)
            else:
                raise Exception(f"No valid price data available for {symbol}")
                
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {str(e)}")
            raise Exception(f"Failed to get current price for {symbol}: {str(e)}")
    
    async def place_order(self, symbol: str, quantity: int, action: str):
        """Place market order - standard community approach"""
        self._ensure_connected()
        
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Qualify the contract to populate conId
            qualified_contracts = await self.ib.qualifyContractsAsync(contract)
            if not qualified_contracts:
                raise Exception(f"Could not qualify contract for {symbol}")
            
            qualified_contract = qualified_contracts[0]
            order = MarketOrder(action.upper(), quantity)
            order.account = self.settings.ibkr_account_id
            
            # Standard order placement
            trade = self.ib.placeOrder(qualified_contract, order)
            await asyncio.sleep(1)  # Brief wait
            
            logger.info(f"Order placed: {action.upper()} {quantity} {symbol}")
            return trade
            
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            raise Exception(f"Failed to place order for {symbol}: {str(e)}")

# Global service instance - community pattern
_ibkr_service: Optional[IBKRService] = None

def get_ibkr_service(settings: Settings = None) -> IBKRService:
    """Get the global IBKR service instance"""
    global _ibkr_service
    if _ibkr_service is None:
        _ibkr_service = IBKRService(settings)
    return _ibkr_service

@asynccontextmanager
async def ibkr_lifespan():
    """Context manager for IBKR service lifecycle - FastAPI standard"""
    settings = Settings()
    service = get_ibkr_service(settings)
    
    # Startup
    await service.start_service()
    
    try:
        yield service
    finally:
        # Shutdown
        await service.stop_service()