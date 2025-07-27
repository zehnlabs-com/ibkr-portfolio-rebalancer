"""
Repository interfaces for data access abstraction
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class IQueueRepository(ABC):
    """Abstract interface for queue data access"""
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to queue storage"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from queue storage"""
        pass
    
    @abstractmethod
    async def get_queue_length(self) -> int:
        """Get current queue length"""
        pass
    
    @abstractmethod
    async def get_active_events_count(self) -> int:
        """Get count of active events"""
        pass
    
    @abstractmethod
    async def get_queue_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from queue"""
        pass
    
    @abstractmethod
    async def remove_event(self, event_id: str) -> bool:
        """Remove specific event from queue"""
        pass
    
    @abstractmethod
    async def add_event(self, account_id: str, exec_command: str, data: Dict[str, Any]) -> str:
        """Add event to queue"""
        pass
    
    @abstractmethod
    async def get_active_events(self) -> List[str]:
        """Get active event keys"""
        pass
    
    
    @abstractmethod
    async def get_oldest_event_age(self) -> Optional[int]:
        """Get age of oldest event in seconds"""
        pass
    
    @abstractmethod
    async def get_retry_events_count(self) -> int:
        """Get count of retry events"""
        pass
    
    @abstractmethod
    async def get_retry_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from retry queue"""
        pass
    
    @abstractmethod
    async def get_delayed_events_count(self) -> int:
        """Get count of delayed events"""
        pass
    
    @abstractmethod
    async def get_delayed_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events from delayed execution queue"""
        pass
    
    @abstractmethod
    async def clear_all_queues(self) -> Dict[str, int]:
        """Clear all events from all queues and return counts of cleared events"""
        pass


class IHealthRepository(ABC):
    """Abstract interface for health data access"""
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to health data source"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from health data source"""
        pass
    
    
    @abstractmethod
    async def get_problematic_events(self, min_retries: int = 2) -> List[Dict[str, Any]]:
        """Get events that have been retried multiple times"""
        pass