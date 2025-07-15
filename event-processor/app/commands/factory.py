"""
Command factory for creating and registering event commands.
"""

from typing import Dict, Any, Type, Optional
from app.commands.base import EventCommand
from app.commands.print_positions import PrintPositionsCommand
from app.commands.print_equity import PrintEquityCommand
from app.commands.print_orders import PrintOrdersCommand
from app.commands.print_rebalance import PrintRebalanceCommand
from app.commands.cancel_orders import CancelOrdersCommand
from app.commands.rebalance import RebalanceCommand
from app.logger import setup_logger

logger = setup_logger(__name__)


class CommandFactory:
    """Factory for creating event processing commands"""
    
    def __init__(self):
        self._commands: Dict[str, Type[EventCommand]] = {}
        self._register_default_commands()
    
    def _register_default_commands(self):
        """Register default command implementations"""
        self.register_command("print-positions", PrintPositionsCommand)
        self.register_command("print-equity", PrintEquityCommand)
        self.register_command("print-orders", PrintOrdersCommand)
        self.register_command("print-rebalance", PrintRebalanceCommand)
        self.register_command("cancel-orders", CancelOrdersCommand)
        self.register_command("rebalance", RebalanceCommand)
    
    def register_command(self, command_type: str, command_class: Type[EventCommand]):
        """Register a command class for a specific command type"""
        self._commands[command_type] = command_class
        logger.debug(f"Registered command: {command_type} -> {command_class.__name__}")
    
    def create_command(self, command_type: str, event_id: str, account_id: str, event_info) -> Optional[EventCommand]:
        """
        Create a command instance for the given command type
        
        Args:
            command_type: The type of command to create
            event_id: Event ID (unused, kept for backward compatibility)
            account_id: Account ID (unused, kept for backward compatibility)
            event_info: Event information object
            
        Returns:
            EventCommand instance or None if command type not found
        """
        if command_type not in self._commands:
            logger.warning(f"Unknown command type: {command_type}")
            return None
        
        command_class = self._commands[command_type]
        try:
            command = command_class(event_info)
            logger.debug(f"Created command: {command}")
            return command
        except Exception as e:
            logger.error(f"Failed to create command {command_type}: {e}")
            return None
    
    def get_registered_commands(self) -> Dict[str, Type[EventCommand]]:
        """Get all registered command types"""
        return self._commands.copy()
    
    def is_command_registered(self, command_type: str) -> bool:
        """Check if a command type is registered"""
        return command_type in self._commands