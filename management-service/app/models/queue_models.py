"""
Pydantic models for queue management API
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class QueueStatus(BaseModel):
    """Queue status response model"""
    queue_length: int
    active_events_count: int
    retry_events_count: int
    delayed_events_count: int
    oldest_event_age_seconds: Optional[int] = None


class QueueEvent(BaseModel):
    """Queue event response model"""
    event_id: str
    account_id: str
    exec_command: str
    times_queued: int
    created_at: str
    type: str  # "active", "retry", or "delayed"
    retry_after: Optional[str] = None  # Only present for retry events
    execution_time: Optional[str] = None  # Only present for delayed events
    data: Dict[str, Any]


class AddEventRequest(BaseModel):
    """Add event request model - flat structure"""
    account_id: str
    exec_command: str    
    eventId: str = "00000000-0000-0000-0000-000000000000"
    strategy_name: str
    cash_reserve_percent: float = 0.0
    
    def to_data_dict(self) -> Dict[str, Any]:
        """Convert to data dictionary excluding base fields"""
        base_fields = {'account_id', 'exec_command'}
        return {k: v for k, v in self.model_dump().items() 
                if k not in base_fields and v is not None}


class AddEventResponse(BaseModel):
    """Add event response model"""
    message: str
    event_id: str


class RemoveEventResponse(BaseModel):
    """Remove event response model"""
    message: str