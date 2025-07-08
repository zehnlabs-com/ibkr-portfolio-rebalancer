"""
Base classes for event processing commands.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum


class CommandStatus(Enum):
    """Status of command execution"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class EventCommandResult:
    """Result of event command execution"""
    status: CommandStatus
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class EventCommand(ABC):
    """Abstract base class for all event processing commands"""
    
    def __init__(self, event_id: str, account_id: str, event_data: Dict[str, Any]):
        self.event_id = event_id
        self.account_id = account_id
        self.event_data = event_data
        self.command_type = self._get_command_type()
    
    @abstractmethod
    def _get_command_type(self) -> str:
        """Return the command type identifier"""
        pass
    
    @abstractmethod
    async def execute(self, services: Dict[str, Any]) -> EventCommandResult:
        """
        Execute the command with provided services
        
        Args:
            services: Dictionary of service instances (ibkr_client, event_service, etc.)
            
        Returns:
            EventCommandResult: The result of command execution
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(event_id={self.event_id}, account_id={self.account_id})"