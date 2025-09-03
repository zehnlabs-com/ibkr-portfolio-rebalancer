"""
Event data models for queue system using Pydantic
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class EventType(str, Enum):
    """Supported event types"""
    REBALANCE = "rebalance"
    PRINT_REBALANCE = "print-rebalance"


class EventData(BaseModel):
    """
    Strongly typed event data for Redis queue storage
    Immutable to ensure thread safety
    """
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)
    
    event_id: str = Field(..., min_length=1, description="Unique event identifier")
    account_id: str = Field(..., min_length=1, description="Account identifier")
    exec_command: EventType = Field(..., description="Command to execute")
    times_queued: int = Field(default=1, ge=1, description="Number of times event has been queued")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="Event creation timestamp")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional event data")
    
    @field_validator('event_id', 'account_id')
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        result = self.model_dump()
        result['exec'] = self.exec_command.value  # Use 'exec' for backward compatibility with existing Redis data
        result['created_at'] = self.created_at.isoformat() if self.created_at else None
        del result['exec_command']  # Remove the enum field
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventData':
        """Create EventData from Redis dictionary"""
        # Handle both 'exec' and 'exec_command' keys for flexibility
        exec_command = data.get('exec') or data.get('exec_command')
        if isinstance(exec_command, str):
            exec_command = EventType(exec_command)
        
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return cls(
            event_id=data['event_id'],
            account_id=data['account_id'],
            exec_command=exec_command,
            times_queued=data.get('times_queued', 1),
            created_at=created_at,
            data=data.get('data', {})
        )
    
    def increment_queue_count(self) -> 'EventData':
        """Create new EventData with incremented queue count"""
        return self.model_copy(update={'times_queued': self.times_queued + 1})


class RetryEventData(EventData):
    """Event data for retry queue with retry timestamp"""
    retry_after: datetime = Field(default_factory=datetime.now, description="When to retry this event")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        result = super().to_dict()
        result['retry_after'] = self.retry_after.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RetryEventData':
        """Create RetryEventData from Redis dictionary"""
        # Handle both 'exec' and 'exec_command' keys for flexibility
        exec_command = data.get('exec') or data.get('exec_command')
        if isinstance(exec_command, str):
            exec_command = EventType(exec_command)
        
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        retry_after = data.get('retry_after')
        if isinstance(retry_after, str):
            retry_after = datetime.fromisoformat(retry_after)
        elif retry_after is None:
            retry_after = datetime.now()
        
        return cls(
            event_id=data['event_id'],
            account_id=data['account_id'],
            exec_command=exec_command,
            times_queued=data.get('times_queued', 1),
            created_at=created_at,
            data=data.get('data', {}),
            retry_after=retry_after
        )


class DelayedEventData(EventData):
    """Event data for delayed execution queue"""
    execution_time: datetime = Field(default_factory=datetime.now, description="When to execute this event")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        result = super().to_dict()
        result['execution_time'] = self.execution_time.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DelayedEventData':
        """Create DelayedEventData from Redis dictionary"""
        # Handle both 'exec' and 'exec_command' keys for flexibility
        exec_command = data.get('exec') or data.get('exec_command')
        if isinstance(exec_command, str):
            exec_command = EventType(exec_command)
        
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        execution_time = data.get('execution_time')
        if isinstance(execution_time, str):
            execution_time = datetime.fromisoformat(execution_time)
        elif execution_time is None:
            execution_time = datetime.now()
        
        return cls(
            event_id=data['event_id'],
            account_id=data['account_id'],
            exec_command=exec_command,
            times_queued=data.get('times_queued', 1),
            created_at=created_at,
            data=data.get('data', {}),
            execution_time=execution_time
        )