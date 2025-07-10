"""
Account configuration model for event processing
"""
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class NotificationConfig:
    channel: str


@dataclass
class RebalancingConfig:
    cash_reserve_percentage: float


@dataclass
class AllocationsConfig:
    url: str


class EventAccountConfig:
    """Account configuration extracted from event payload"""
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize from event payload account_config data"""
        self.account_id = data.get('account_id')
        self.notification = NotificationConfig(channel=data.get('notification_channel'))
        self.rebalancing = RebalancingConfig(
            cash_reserve_percentage=data.get('cash_reserve_percentage', data.get('equity_reserve_percentage', 1.0))
        )
        self.allocations = AllocationsConfig(url=data.get('allocations_url'))