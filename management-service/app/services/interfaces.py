"""
Service interfaces for business logic abstraction
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class IQueueService(ABC):
    """Abstract interface for queue management business logic"""
    
    @abstractmethod
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get comprehensive queue status"""
        pass
    
    @abstractmethod
    async def get_queue_events(self, limit: int = 100, event_type: str = None) -> List[Dict[str, Any]]:
        """Get events from queue with details and optional type filtering"""
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
    async def clear_all_queues(self) -> Dict[str, int]:
        """Clear all events from all queues and return counts of cleared events"""
        pass


class IHealthService(ABC):
    """Abstract interface for health checking business logic"""
    
    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Check system health"""
        pass
    
    @abstractmethod
    async def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health information"""
        pass
    
    @abstractmethod
    async def get_problematic_events(self, min_retries: int = 2) -> List[Dict[str, Any]]:
        """Get problematic events"""
        pass


class IAuthenticationService(ABC):
    """Abstract interface for authentication"""
    
    @abstractmethod
    def verify_api_key(self, api_key: str) -> bool:
        """Verify API key"""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if authentication is configured"""
        pass