from pydantic import BaseModel, Field, validator
from typing import List, Optional
from decimal import Decimal


class AllocationRequest(BaseModel):
    symbol: str
    allocation: Decimal = Field(ge=Decimal('0.0'), le=Decimal('1.0'))
    
    @validator('allocation', pre=True)
    def convert_to_decimal(cls, v):
        return Decimal(str(v))


class RebalanceRequest(BaseModel):
    allocations: List[AllocationRequest]
    
    @validator('allocations')
    def validate_allocations_sum(cls, v):
        total = sum(alloc.allocation for alloc in v)
        if abs(total - Decimal('1.0')) > Decimal('0.0001'):
            raise ValueError(f"Allocations must sum to exactly 1.0, got {total}")
        return v


class MarketData(BaseModel):
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    
    @validator('bid', 'ask', 'last', pre=True)
    def convert_to_decimal(cls, v):
        return Decimal(str(v))


class Position(BaseModel):
    symbol: str
    quantity: Decimal
    market_value: Decimal
    avg_cost: Decimal
    
    @validator('quantity', 'market_value', 'avg_cost', pre=True)
    def convert_to_decimal(cls, v):
        return Decimal(str(v))


class Trade(BaseModel):
    symbol: str
    action: str  # BUY or SELL
    quantity: Decimal
    order_type: str = "MKT"
    price: Optional[Decimal] = None
    trade_value: Optional[Decimal] = None
    
    @validator('quantity', 'price', 'trade_value', pre=True)
    def convert_to_decimal(cls, v):
        if v is None:
            return v
        return Decimal(str(v))


class RebalanceResponse(BaseModel):
    success: bool
    message: str
    trades: List[Trade] = []
    total_portfolio_value: Decimal = Decimal('0.0')
    
    @validator('total_portfolio_value', pre=True)
    def convert_to_decimal(cls, v):
        return Decimal(str(v))