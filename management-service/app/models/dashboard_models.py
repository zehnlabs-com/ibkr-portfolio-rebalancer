"""
Data models for dashboard API responses
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Position(BaseModel):
    """Individual position within an account"""
    symbol: str = Field(description="Stock symbol")
    quantity: float = Field(description="Number of shares held")
    market_value: float = Field(description="Current market value of position")
    avg_cost: float = Field(description="Average cost basis per share")
    current_price: float = Field(description="Current market price per share")
    unrealized_pnl: float = Field(description="Unrealized profit/loss in dollars")
    unrealized_pnl_percent: float = Field(description="Unrealized profit/loss as percentage")


class AccountData(BaseModel):
    """Complete account data for dashboard"""
    account_id: str = Field(description="Account identifier")
    current_value: float = Field(description="Current net liquidation value")
    last_close_netliq: float = Field(description="Previous close net liquidation value")
    todays_pnl: float = Field(description="Today's profit/loss in dollars")
    todays_pnl_percent: float = Field(description="Today's profit/loss as percentage")
    positions: List[Position] = Field(description="List of current positions")
    positions_count: int = Field(description="Number of positions")
    last_update: datetime = Field(description="Timestamp of last data update")
    
    @property
    def enabled(self) -> bool:
        """Account enabled status (derived from positions_count > 0)"""
        return self.positions_count > 0


class AccountSummary(BaseModel):
    """Summary data for accounts list"""
    account_id: str = Field(description="Account identifier")
    current_value: float = Field(description="Current net liquidation value")
    todays_pnl: float = Field(description="Today's profit/loss in dollars")
    todays_pnl_percent: float = Field(description="Today's profit/loss as percentage")
    positions_count: int = Field(description="Number of positions")
    last_update: datetime = Field(description="Timestamp of last data update")


class DashboardOverview(BaseModel):
    """System-wide dashboard overview"""
    total_accounts: int = Field(description="Total number of accounts")
    total_value: float = Field(description="Combined value across all accounts")
    total_pnl: float = Field(description="Combined P&L across all accounts")
    total_pnl_percent: float = Field(description="Combined P&L percentage")
    accounts: List[AccountSummary] = Field(description="Summary of all accounts")
    last_update: datetime = Field(description="Timestamp of last system update")