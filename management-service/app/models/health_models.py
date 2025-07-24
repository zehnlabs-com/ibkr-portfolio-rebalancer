"""
Pydantic models for health checking API
"""
from typing import Dict, Any, List
from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Health check response model"""
    status: str
    healthy: bool
    events_with_retries: int
    retry_events: int
    message: str


class DetailedHealthStatus(BaseModel):
    """Detailed health check response model"""
    status: str
    healthy: bool
    queue_length: int
    active_events_count: int
    retry_events_count: int
    total_events: int
    events_with_retries: int
    max_retry_count: int
    retry_distribution: Dict[str, int]
    message: str


class ProblematicEvent(BaseModel):
    """Problematic event model"""
    event_id: str
    account_id: str
    exec_command: str
    times_queued: int
    created_at: str
    data: Dict[str, Any]