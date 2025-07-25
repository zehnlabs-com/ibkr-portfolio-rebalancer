"""
Account configuration model for event processing
"""
from typing import Dict, Any
class EventAccountConfig:
    """Account configuration extracted from event payload"""
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize from flat event payload data"""
        self.account_id = data.get('account_id')
        self.strategy_name = data.get('strategy_name')  
        self.cash_reserve_percent = data.get('cash_reserve_percent', 0.0)
        