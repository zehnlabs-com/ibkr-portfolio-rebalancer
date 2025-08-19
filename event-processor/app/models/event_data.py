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
    PRINT_POSITIONS = "print-positions"
    PRINT_EQUITY = "print-equity"
    PRINT_ORDERS = "print-orders"
    PRINT_REBALANCE = "print-rebalance"
    CANCEL_ORDERS = "cancel-orders"


class EventData(BaseModel):
    """
    Strongly typed event data for Redis queue storage
    """
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)
    
    event_id: str = Field(..., min_length=1, description="Unique event identifier")
    account_id: str = Field(..., min_length=1, description="Account identifier")
    exec_command: EventType = Field(..., description="Command to execute")
    times_queued: int = Field(default=1, ge=1, description="Number of times event was queued")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="Event creation timestamp")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional event data")
    
    @field_validator('event_id', 'account_id')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Value cannot be empty")
        return v.strip()
    
    @field_validator('times_queued')
    @classmethod
    def validate_times_queued(cls, v: int) -> int:
        if v < 1:
            raise ValueError("times_queued must be at least 1")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage with backward compatibility"""
        result = self.model_dump()
        result['exec'] = self.exec_command.value  # Use 'exec' for backward compatibility
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
        return EventData(
            event_id=self.event_id,
            account_id=self.account_id,
            exec_command=self.exec_command,
            times_queued=self.times_queued + 1,
            created_at=self.created_at,
            data=self.data
        )

