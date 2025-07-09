from typing import Dict, Any, Optional
from datetime import datetime, date, timezone
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
    times_queued: int
    created_at: datetime

    @classmethod
    def create_new(cls, account_id: str, payload: Dict[str, Any], times_queued: int = 1) -> 'RebalanceEvent':
        now = datetime.now(timezone.utc)
        return cls(
            event_id=str(uuid.uuid4()),
            account_id=account_id,
            status='pending',
            payload=payload,
            received_at=now,
            times_queued=times_queued,
            created_at=now
        )