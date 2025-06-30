from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class RebalanceOrder(BaseModel):
    symbol: str
    quantity: int
    action: str  # BUY or SELL
    market_value: float
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "quantity": 10,
                "action": "BUY",
                "market_value": 1500.00
            }
        }

class RebalanceResponse(BaseModel):
    account_id: str
    execution_mode: str
    orders: List[RebalanceOrder]
    status: str
    message: str
    timestamp: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "account_id": "DU123456",
                "execution_mode": "dry_run",
                "orders": [
                    {
                        "symbol": "AAPL",
                        "quantity": 10,
                        "action": "BUY",
                        "market_value": 1500.00
                    }
                ],
                "status": "success",
                "message": "Rebalancing completed successfully",
                "timestamp": "2023-12-01T10:00:00Z"
            }
        }

class AccountInfo(BaseModel):
    account_id: str
    notification_channel: str
    allocations_url: str
    
class AccountsResponse(BaseModel):
    accounts: List[AccountInfo]
    
class PositionInfo(BaseModel):
    symbol: str
    position: float
    market_value: float
    avg_cost: float
    
class PositionsResponse(BaseModel):
    account_id: str
    positions: List[PositionInfo]
    timestamp: datetime
    
class AccountValueResponse(BaseModel):
    account_id: str
    net_liquidation: float
    timestamp: datetime
    
class HealthResponse(BaseModel):
    status: str
    ibkr_connected: bool
    timestamp: datetime
    message: Optional[str] = None