from pydantic import BaseModel, Field, validator
from typing import List, Literal

class AllocationRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    allocation: float = Field(..., ge=0, le=1, description="Target allocation (0-1)")

class RebalanceRequest(BaseModel):
    allocations: List[AllocationRequest]
    
    @validator('allocations')
    def validate_total_allocation(cls, v):
        total = sum(item.allocation for item in v)
        if not 0.99 <= total <= 1.01:  # Allow small rounding errors
            raise ValueError("Total allocation must equal 1.0")
        return v

class CalculatedOrder(BaseModel):
    side: Literal["buy", "sell"] = Field(..., description="Order side")
    ticker: str = Field(..., description="Stock ticker symbol")
    price: float = Field(..., description="Current market price")
    quantity: int = Field(..., description="Number of shares to trade")
    allocation: float = Field(..., description="Target allocation for this symbol")
    current_value: float = Field(default=0, description="Current position value")
    target_value: float = Field(..., description="Target position value")

class CalculateResponse(BaseModel):
    success: bool
    message: str
    total_portfolio_value: float
    orders: List[CalculatedOrder] = []

class RebalanceResponse(BaseModel):
    success: bool
    message: str
    trades_executed: List[dict] = []