from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

class RebalanceOrder(BaseModel):
    symbol: str
    quantity: int
    action: str  # BUY or SELL
    market_value: float

class CancelledOrder(BaseModel):
    order_id: str
    symbol: str
    quantity: int
    action: str  # BUY or SELL
    order_type: str
    status: str

class AccountEquityInfo(BaseModel):
    total_equity: float
    reserve_percentage: float
    reserve_amount: float
    available_for_trading: float

class RebalanceResponse(BaseModel):
    account_id: str
    execution_mode: str
    equity_info: AccountEquityInfo
    orders: List[RebalanceOrder]
    cancelled_orders: List[CancelledOrder]
    status: str
    message: str
    timestamp: datetime

