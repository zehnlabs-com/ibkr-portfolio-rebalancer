"""
Account and position data models for dashboard system
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class PositionData(BaseModel):
    """
    Strongly typed position data for portfolio tracking
    Immutable to ensure thread safety
    """
    symbol: str = Field(..., min_length=1, description="Stock symbol")
    position: float = Field(..., description="Number of shares")
    market_price: float = Field(..., ge=0, description="Current market price")
    market_value: float = Field(..., description="Current market value")
    avg_cost: float = Field(..., description="Average cost per share")
    cost_basis: float = Field(..., description="Total cost basis")
    unrealized_pnl: float = Field(..., description="Unrealized P&L")
    unrealized_pnl_percent: float = Field(..., description="Unrealized P&L percentage")
    weight: float = Field(..., description="Weight in portfolio")
    
    @validator('position')
    def position_cannot_be_zero(cls, v):
        if v == 0:
            raise ValueError('position cannot be zero')
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PositionData':
        """Create PositionData from Redis dictionary"""
        return cls(**data)
    
    class Config:
        frozen = True  # Make immutable like dataclass(frozen=True)


class AccountData(BaseModel):
    """
    Strongly typed account data for dashboard system
    Immutable to ensure thread safety
    """
    account_id: str = Field(..., min_length=1, description="Account identifier")
    account_name: str = Field(..., min_length=1, description="Account name")
    strategy_name: Optional[str] = Field(None, description="Strategy name")
    is_ira: bool = Field(..., description="Whether account is IRA")
    net_liquidation: float = Field(..., gt=0, description="Net liquidation value")
    cash_balance: float = Field(..., description="Cash balance")
    todays_pnl: float = Field(..., description="Today's P&L")
    todays_pnl_percent: float = Field(..., description="Today's P&L percentage")
    total_upnl: float = Field(..., description="Total unrealized P&L")
    total_upnl_percent: float = Field(..., description="Total unrealized P&L percentage")
    invested_amount: float = Field(..., description="Total invested amount")
    cash_percent: float = Field(..., description="Cash percentage")
    last_updated: datetime = Field(..., description="Last update timestamp")
    positions: List[PositionData] = Field(default_factory=list, description="Account positions")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        result = self.dict()
        result['last_updated'] = self.last_updated.isoformat()
        result['positions'] = [pos.to_dict() for pos in self.positions]
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccountData':
        """Create AccountData from Redis dictionary"""
        data_copy = data.copy()
        
        # Handle datetime parsing
        last_updated = data_copy.get('last_updated')
        if isinstance(last_updated, str):
            data_copy['last_updated'] = datetime.fromisoformat(last_updated)
        elif last_updated is None:
            data_copy['last_updated'] = datetime.now()
        
        # Handle positions
        positions_data = data_copy.get('positions', [])
        data_copy['positions'] = [
            PositionData.from_dict(pos_data) if isinstance(pos_data, dict) else pos_data
            for pos_data in positions_data
        ]
        
        return cls(**data_copy)
    
    def get_position_by_symbol(self, symbol: str) -> Optional[PositionData]:
        """Get position data by symbol"""
        return next((pos for pos in self.positions if pos.symbol == symbol), None)
    
    def get_total_position_count(self) -> int:
        """Get total number of positions"""
        return len(self.positions)
    
    def get_total_market_value(self) -> float:
        """Get total market value of all positions"""
        return sum(pos.market_value for pos in self.positions)
    
    class Config:
        frozen = True  # Make immutable like dataclass(frozen=True)


class DashboardSummary(BaseModel):
    """
    Dashboard summary data aggregating all accounts
    """
    total_value: float = Field(..., ge=0, description="Total portfolio value")
    total_pnl_today: float = Field(..., description="Total P&L today")
    total_pnl_today_percent: float = Field(..., description="Total P&L today percentage")
    total_accounts: int = Field(..., ge=0, description="Number of accounts")
    last_updated: datetime = Field(..., description="Last update timestamp")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        result = self.dict()
        result['last_updated'] = self.last_updated.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DashboardSummary':
        """Create DashboardSummary from Redis dictionary"""
        data_copy = data.copy()
        
        # Handle datetime parsing
        last_updated = data_copy.get('last_updated')
        if isinstance(last_updated, str):
            data_copy['last_updated'] = datetime.fromisoformat(last_updated)
        elif last_updated is None:
            data_copy['last_updated'] = datetime.now()
        
        return cls(**data_copy)
    
    class Config:
        frozen = True  # Make immutable like dataclass(frozen=True)