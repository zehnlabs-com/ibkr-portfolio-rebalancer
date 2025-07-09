from typing import Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel

class QueueEvent(BaseModel):
    event_id: str
    account_id: str
    data: Dict[str, Any]
    retry_count: int = 0
    first_failed_date: datetime = None
    times_queued: int
    created_at: datetime

class ProcessingResult(BaseModel):
    event_id: str
    account_id: str
    status: str  # 'completed', 'failed', 'retry'
    error_message: str = None
    orders_placed: int = 0
    processing_time: float = 0.0