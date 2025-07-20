from typing import Dict, Any, Optional
from datetime import datetime, date
import uuid
from pydantic import BaseModel

class EventInfo(BaseModel):
    event_id: str
    account_id: str
    exec_command: str  # The command to execute (e.g., 'rebalance', 'print-positions')
    status: str  # 'pending', 'processing', 'completed', 'failed'
    payload: Dict[str, Any]
    received_at: datetime
    times_queued: int
    created_at: datetime

    @classmethod
    def create_new(cls, account_id: str, exec_command: str, payload: Dict[str, Any], times_queued: int = 1) -> 'EventInfo':
        now = datetime.now()
        return cls(
            event_id=str(uuid.uuid4()),
            account_id=account_id,
            exec_command=exec_command,
            status='pending',
            payload=payload,
            received_at=now,
            times_queued=times_queued,
            created_at=now
        )