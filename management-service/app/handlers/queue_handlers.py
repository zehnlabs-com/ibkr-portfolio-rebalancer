"""
Queue management API handlers
"""
import logging
from typing import List
from fastapi import HTTPException, status, Depends

from app.services.interfaces import IQueueService
from app.models.queue_models import QueueStatus, QueueEvent, AddEventRequest, AddEventResponse, RemoveEventResponse, ClearQueuesResponse

logger = logging.getLogger(__name__)


class QueueHandlers:
    """Queue API handlers"""
    
    def __init__(self, queue_service: IQueueService):
        self.queue_service = queue_service
    
    async def get_queue_status(self) -> QueueStatus:
        """Get queue status"""
        try:
            status_data = await self.queue_service.get_queue_status()
            return QueueStatus(**status_data)
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get queue status: {str(e)}"
            )
    
    async def get_queue_events(self, limit: int = 100, event_type: str = None) -> List[QueueEvent]:
        """Get events from queue with optional type filtering"""
        try:
            if event_type and event_type not in ["active", "retry", "delayed"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid event type. Must be 'active', 'retry', or 'delayed'"
                )
            
            events = await self.queue_service.get_queue_events(limit=limit, event_type=event_type)
            return [QueueEvent(**event) for event in events]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get queue events: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get queue events: {str(e)}"
            )
    
    async def remove_event(self, event_id: str) -> RemoveEventResponse:
        """Remove event from queue"""
        try:
            success = await self.queue_service.remove_event(event_id)
            if success:
                return RemoveEventResponse(message=f"Event {event_id} removed successfully")
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Event {event_id} not found in queue"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to remove event {event_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to remove event: {str(e)}"
            )
    
    async def add_event(self, event_request: AddEventRequest) -> AddEventResponse:
        """Add event to queue"""
        try:
            event_id = await self.queue_service.add_event(
                account_id=event_request.account_id,
                exec_command=event_request.exec_command,
                data=event_request.to_data_dict()
            )
            return AddEventResponse(
                message="Event added successfully",
                event_id=event_id
            )
        except Exception as e:
            logger.error(f"Failed to add event: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to add event: {str(e)}"
            )
    
    async def clear_all_queues(self) -> ClearQueuesResponse:
        """Clear all events from all queues"""
        try:
            cleared_counts = await self.queue_service.clear_all_queues()
            total_cleared = sum(cleared_counts.values())
            
            return ClearQueuesResponse(
                message=f"Successfully cleared {total_cleared} events from all queues",
                cleared_counts=cleared_counts
            )
        except Exception as e:
            logger.error(f"Failed to clear all queues: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to clear all queues: {str(e)}"
            )