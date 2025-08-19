"""
Account configuration model for event processing
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class EventAccountConfig(BaseModel):
    """Account configuration extracted from event payload"""
    
    account_id: Optional[str] = Field(None, description="Account identifier")
    strategy_name: Optional[str] = Field(None, description="Strategy name")
    cash_reserve_percent: float = Field(default=0.0, ge=0, le=100, description="Cash reserve percentage")
    replacement_set: Optional[str] = Field(None, description="ETF replacement set for IRA accounts")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventAccountConfig':
        """Create EventAccountConfig from event payload data"""
        return cls(
            account_id=data.get('account_id'),
            strategy_name=data.get('strategy_name'),
            cash_reserve_percent=data.get('cash_reserve_percent', 0.0),
            replacement_set=data.get('replacement_set')
        )
    
    class Config:
        frozen = True  # Make immutable
        