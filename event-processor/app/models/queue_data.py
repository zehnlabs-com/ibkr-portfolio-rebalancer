"""
Queue system data models for Redis operations
"""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class QueueStats(BaseModel):
    """
    Strongly typed queue statistics for monitoring
    """
    active_queue: int = Field(..., ge=0, description="Number of active queue items")
    retry_queue: int = Field(..., ge=0, description="Number of retry queue items")
    delayed_queue: int = Field(..., ge=0, description="Number of delayed queue items")
    active_events_set: int = Field(..., ge=0, description="Number of active events")
    timestamp: datetime = Field(..., description="Statistics timestamp")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        result = self.dict()
        result['timestamp'] = self.timestamp.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueueStats':
        """Create QueueStats from Redis data"""
        data_copy = data.copy()
        
        # Handle datetime parsing
        timestamp = data_copy.get('timestamp')
        if isinstance(timestamp, str):
            data_copy['timestamp'] = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            data_copy['timestamp'] = datetime.now()
        
        # Ensure all counts are present with defaults
        data_copy.setdefault('active_queue', 0)
        data_copy.setdefault('retry_queue', 0)
        data_copy.setdefault('delayed_queue', 0)
        data_copy.setdefault('active_events_set', 0)
        
        return cls(**data_copy)
    
    class Config:
        frozen = True  # Make immutable like dataclass(frozen=True)
    
    def get_total_pending(self) -> int:
        """Get total pending events across all queues"""
        return self.active_queue + self.retry_queue + self.delayed_queue


class QueueEventSummary(BaseModel):
    """
    Summary data for queue events in management API
    """
    event_id: str = Field(..., min_length=1, description="Event identifier")
    account_id: str = Field(..., min_length=1, description="Account identifier")
    exec_command: str = Field(..., min_length=1, description="Execution command")
    times_queued: int = Field(..., ge=1, description="Number of times queued")
    created_at: str = Field(..., description="Creation timestamp string")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")
    retry_after: Optional[str] = Field(None, description="Retry after timestamp")
    execution_time: Optional[str] = Field(None, description="Execution timestamp")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueueEventSummary':
        """Create QueueEventSummary from Redis data"""
        data_copy = data.copy()
        
        # Handle exec_command field compatibility
        if 'exec_command' not in data_copy:
            data_copy['exec_command'] = data_copy.get('exec', '')
        
        # Provide defaults for required fields
        data_copy.setdefault('times_queued', 1)
        data_copy.setdefault('created_at', '')
        data_copy.setdefault('data', {})
        
        return cls(**data_copy)
    
    class Config:
        frozen = True  # Make immutable like dataclass(frozen=True)


