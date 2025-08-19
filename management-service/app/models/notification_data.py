"""
Notification data models for user notification system using Pydantic
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
import uuid


class NotificationType(str, Enum):
    """Supported notification types"""
    EVENT_STARTED = "event_started"
    EVENT_COMPLETED = "event_completed" 
    EVENT_FAILED = "event_failed"
    EVENT_RETRY = "event_retry"
    SYSTEM_ERROR = "system_error"
    SYSTEM_INFO = "system_info"


class NotificationData(BaseModel):
    """
    Strongly typed notification data for user notifications
    Immutable to ensure thread safety
    """
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)
    
    notification_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique notification identifier")
    account_id: str = Field(default="", description="Account identifier")
    strategy_name: Optional[str] = Field(default=None, description="Strategy name if applicable")
    event_type: Optional[NotificationType] = Field(default=None, description="Type of notification")
    message: str = Field(default="", description="Notification message")
    markdown_body: str = Field(default="", description="Detailed notification body in markdown")
    created_at: datetime = Field(default_factory=datetime.now, description="Notification creation timestamp")
    is_read: bool = Field(default=False, description="Whether notification has been read")
    
    @field_validator('notification_id', 'message', 'markdown_body')
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        if v and not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip() if v else v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        result = self.model_dump()
        result['event_type'] = self.event_type.value if self.event_type else None
        result['created_at'] = self.created_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationData':
        """Create NotificationData from Redis dictionary"""
        event_type = data.get('event_type')
        if isinstance(event_type, str):
            event_type = NotificationType(event_type)
        
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
        
        return cls(
            notification_id=data.get('notification_id', str(uuid.uuid4())),
            account_id=data.get('account_id', ''),
            strategy_name=data.get('strategy_name'),
            event_type=event_type,
            message=data.get('message', ''),
            markdown_body=data.get('markdown_body', ''),
            created_at=created_at,
            is_read=bool(data.get('is_read', False))
        )
    
    def mark_as_read(self) -> 'NotificationData':
        """Create new NotificationData marked as read"""
        return self.model_copy(update={'is_read': True})


class IBKRErrorData(BaseModel):
    """
    Strongly typed IBKR error data for error tracking
    """
    model_config = ConfigDict(frozen=True)
    
    request_id: int = Field(..., gt=0, description="IBKR request ID")
    error_code: int = Field(..., gt=0, description="IBKR error code")
    error_string: str = Field(..., min_length=1, description="Error message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    advanced_order_reject_json: Optional[str] = Field(default=None, description="Advanced order rejection JSON")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        result = self.model_dump()
        result['timestamp'] = self.timestamp.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IBKRErrorData':
        """Create IBKRErrorData from Redis dictionary"""
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()
        
        return cls(
            request_id=int(data['request_id']),
            error_code=int(data['error_code']),
            error_string=data['error_string'],
            timestamp=timestamp,
            advanced_order_reject_json=data.get('advanced_order_reject_json')
        )