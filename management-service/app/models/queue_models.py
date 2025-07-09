"""
Pydantic models for queue management API
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class QueueStatus(BaseModel):
    """Queue status response model"""
    queue_length: int
    active_events_count: int
    oldest_event_age_seconds: Optional[int] = None
    events_with_retries: int


class QueueEvent(BaseModel):
    """Queue event response model"""
    event_id: str
    account_id: str
    exec_command: str
    times_queued: int
    created_at: str
    data: Dict[str, Any]


class AddEventRequest(BaseModel):
    """Add event request model"""
    account_id: str
    exec_command: str
    data: Dict[str, Any]


class AddEventResponse(BaseModel):
    """Add event response model"""
    message: str
    event_id: str


class RemoveEventResponse(BaseModel):
    """Remove event response model"""
    message: str