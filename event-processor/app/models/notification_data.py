"""
Notification data models for user notification system
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
import uuid
from pydantic import BaseModel, Field, validator


class NotificationType(Enum):
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
    notification_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique notification ID")
    account_id: str = Field(default="", description="Account identifier")
    strategy_name: Optional[str] = Field(None, description="Strategy name")
    event_type: Optional[NotificationType] = Field(None, description="Type of notification")
    message: str = Field(..., min_length=1, description="Notification message")
    markdown_body: str = Field(..., min_length=1, description="Markdown body content")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    is_read: bool = Field(default=False, description="Whether notification has been read")
    
    @validator('notification_id')
    def notification_id_cannot_be_empty(cls, v):
        if not v:
            raise ValueError('notification_id cannot be empty')
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        result = self.dict()
        result['event_type'] = self.event_type.value if self.event_type else None
        result['created_at'] = self.created_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationData':
        """Create NotificationData from Redis dictionary"""
        data_copy = data.copy()
        
        # Handle enum parsing
        event_type = data_copy.get('event_type')
        if isinstance(event_type, str):
            data_copy['event_type'] = NotificationType(event_type)
        
        # Handle datetime parsing
        created_at = data_copy.get('created_at')
        if isinstance(created_at, str):
            data_copy['created_at'] = datetime.fromisoformat(created_at)
        elif created_at is None:
            data_copy['created_at'] = datetime.now()
        
        # Provide defaults for required fields if missing
        if 'notification_id' not in data_copy or not data_copy['notification_id']:
            data_copy['notification_id'] = str(uuid.uuid4())
        if 'account_id' not in data_copy:
            data_copy['account_id'] = ''
        if 'message' not in data_copy:
            data_copy['message'] = 'No message'
        if 'markdown_body' not in data_copy:
            data_copy['markdown_body'] = 'No content'
        if 'is_read' not in data_copy:
            data_copy['is_read'] = False
        
        return cls(**data_copy)
    
    def mark_as_read(self) -> 'NotificationData':
        """Create new NotificationData marked as read"""
        return self.copy(update={'is_read': True})
    
    class Config:
        frozen = True  # Make immutable like dataclass(frozen=True)


