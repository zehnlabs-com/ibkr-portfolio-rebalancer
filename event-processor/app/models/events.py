from typing import Dict, Any, Optional
from datetime import datetime, date
import uuid
from pydantic import BaseModel

class RebalanceEvent(BaseModel):
    event_id: str
    account_id: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    payload: Dict[str, Any]
    error_message: Optional[str] = None
    received_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    first_failed_date: Optional[date] = None
    created_at: datetime = datetime.utcnow()

    @classmethod
    def create_new(cls, account_id: str, payload: Dict[str, Any]) -> 'RebalanceEvent':
        return cls(
            event_id=str(uuid.uuid4()),
            account_id=account_id,
            status='pending',
            payload=payload,
            received_at=datetime.utcnow()
        )