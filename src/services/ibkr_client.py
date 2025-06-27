import httpx
import os
from typing import List, Dict, Any
from decimal import Decimal
from ..models.portfolio import Position, Trade, MarketData


class IBKRClient:
    def __init__(self):
        self.base_url = os.getenv("IBKR_BASE_URL", "http://localhost:5000")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        response = await self.client.get(f"{self.base_url}/v1/api/portfolio/accounts")
        response.raise_for_status()
        return response.json()
    
    async def get_positions(self) -> List[Position]:
        """Get current portfolio positions"""
        accounts = await self.get_account_info()
        if not accounts:
            return []
        
        account_id = accounts[0]["id"]
        response = await self.client.get(f"{self.base_url}/v1/api/portfolio/{account_id}/positions/0")
        response.raise_for_status()
        
        positions = []
        for pos in response.json():
            if pos.get("position", 0) != 0:
                positions.append(Position(
                    symbol=pos["contractDesc"],
                    quantity=Decimal(str(pos["position"])),
                    market_value=Decimal(str(pos["mktValue"])),
                    avg_cost=Decimal(str(pos["avgCost"]))
                ))
        
        return positions
    
    async def get_portfolio_value(self) -> Decimal:
        """Get total portfolio value"""
        accounts = await self.get_account_info()
        if not accounts:
            return Decimal('0.0')
        
        account_id = accounts[0]["id"]
        response = await self.client.get(f"{self.base_url}/v1/api/portfolio/{account_id}/ledger")
        response.raise_for_status()
        
        ledger = response.json()
        value = ledger.get("BASE", {}).get("netliquidationvalue", {}).get("value", 0)
        return Decimal(str(value))
    
    async def place_order(self, trade: Trade, account_id: str) -> Dict[str, Any]:
        """Place a trade order"""
        order_data = {
            "orders": [{
                "conid": await self._get_contract_id(trade.symbol),
                "secType": "STK",
                "side": trade.action,
                "quantity": int(abs(trade.quantity)),
                "orderType": trade.order_type,
                "tif": "DAY"
            }]
        }
        
        # Add price for limit orders
        if trade.order_type == "LMT" and trade.price:
            order_data["orders"][0]["price"] = float(trade.price)
        
        response = await self.client.post(
            f"{self.base_url}/v1/api/iserver/account/{account_id}/orders",
            json=order_data
        )
        response.raise_for_status()
        return response.json()
    
    async def _get_contract_id(self, symbol: str) -> int:
        """Get contract ID for a symbol"""
        response = await self.client.get(
            f"{self.base_url}/v1/api/iserver/secdef/search",
            params={"symbol": symbol, "name": "true"}
        )
        response.raise_for_status()
        
        results = response.json()
        if results and len(results) > 0:
            return results[0]["conid"]
        
        raise ValueError(f"Contract not found for symbol: {symbol}")
    
    async def get_market_data(self, symbol: str) -> MarketData:
        """Get market data for a symbol"""
        conid = await self._get_contract_id(symbol)
        
        # Get market data snapshot
        response = await self.client.get(
            f"{self.base_url}/v1/api/iserver/marketdata/snapshot",
            params={"conids": str(conid), "fields": "31,84,86"}  # 31=bid, 84=ask, 86=last
        )
        response.raise_for_status()
        
        data = response.json()
        if not data or len(data) == 0:
            raise ValueError(f"No market data found for symbol: {symbol}")
        
        market_info = data[0]
        
        # Extract bid, ask, last prices
        bid = Decimal(str(market_info.get("31", 0)))  # bid
        ask = Decimal(str(market_info.get("84", 0)))  # ask  
        last = Decimal(str(market_info.get("86", 0)))  # last
        
        # Fallback logic if some prices are missing
        if last == 0:
            last = (bid + ask) / 2 if bid > 0 and ask > 0 else bid or ask
        if bid == 0:
            bid = last
        if ask == 0:
            ask = last
            
        if last == 0:
            raise ValueError(f"No valid price data for symbol: {symbol}")
        
        return MarketData(
            symbol=symbol,
            bid=bid,
            ask=ask,
            last=last
        )
    
    async def get_multiple_market_data(self, symbols: List[str]) -> Dict[str, MarketData]:
        """Get market data for multiple symbols efficiently"""
        market_data = {}
        
        # Get contract IDs for all symbols
        conids = []
        symbol_to_conid = {}
        
        for symbol in symbols:
            try:
                conid = await self._get_contract_id(symbol)
                conids.append(str(conid))
                symbol_to_conid[conid] = symbol
            except Exception:
                # Skip symbols that can't be found
                continue
        
        if not conids:
            return market_data
        
        # Get market data for all symbols in one request
        response = await self.client.get(
            f"{self.base_url}/v1/api/iserver/marketdata/snapshot",
            params={"conids": ",".join(conids), "fields": "31,84,86"}
        )
        response.raise_for_status()
        
        data = response.json()
        
        for item in data:
            conid = item.get("conid")
            if conid not in symbol_to_conid:
                continue
                
            symbol = symbol_to_conid[conid]
            
            try:
                bid = Decimal(str(item.get("31", 0)))
                ask = Decimal(str(item.get("84", 0)))
                last = Decimal(str(item.get("86", 0)))
                
                # Fallback logic
                if last == 0:
                    last = (bid + ask) / 2 if bid > 0 and ask > 0 else bid or ask
                if bid == 0:
                    bid = last
                if ask == 0:
                    ask = last
                    
                if last > 0:
                    market_data[symbol] = MarketData(
                        symbol=symbol,
                        bid=bid,
                        ask=ask,
                        last=last
                    )
            except Exception:
                # Skip symbols with invalid data
                continue
        
        return market_data
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()