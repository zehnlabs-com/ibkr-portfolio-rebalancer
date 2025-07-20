import logging
import sys
import json
from datetime import datetime
from app.config import config

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging with event_id support"""
    
    def format(self, record):
        # Start with basic log structure
        log_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z'),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage()
        }
        
        # Add event_id if present in extra
        if hasattr(record, 'event_id'):
            log_data['event_id'] = record.event_id
            
        # Add account_id if present in extra
        if hasattr(record, 'account_id'):
            log_data['account_id'] = record.account_id
            
        # Add any other extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info', 'message', 'event_id', 'account_id']:
                # Convert datetime objects to ISO format strings with timezone info for JSON serialization
                if isinstance(value, datetime):
                    log_data[key] = value.strftime('%Y-%m-%d %H:%M:%S %Z') if value.tzinfo else value.strftime('%Y-%m-%d %H:%M:%S %Z')
                else:
                    log_data[key] = value
        
        if config.logging.format == 'json':
            return json.dumps(log_data)
        else:
            # Standard format with event_id if present
            base_msg = f"{log_data['timestamp']} - {log_data['logger']} - {log_data['level']} - {log_data['message']}"
            if 'event_id' in log_data:
                base_msg += f" [event_id={log_data['event_id']}]"
            if 'account_id' in log_data:
                base_msg += f" [account_id={log_data['account_id']}]"
            return base_msg

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, config.logging.level.upper()))
    
    handler = logging.StreamHandler(sys.stdout)
    formatter = StructuredFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

def _extract_event_properties(event):
    """Extract relevant properties from an event object for logging"""
    if event is None:
        return {}
    
    # Since EventInfo objects are strongly typed, we can directly access core properties
    properties = {
        'event_id': event.event_id,
        'account_id': event.account_id,
        'exec_command': event.exec_command,
        'status': event.status,
        'times_queued': event.times_queued,
        'received_at': event.received_at.strftime('%Y-%m-%d %H:%M:%S %Z') if isinstance(event.received_at, datetime) else event.received_at
    }
    
    return properties

class EventLogger:
    """Logger instance for event-based logging with automatic event context extraction"""
    
    def __init__(self, name: str):
        self.logger = setup_logger(name)
    
    def log_debug(self, message: str, event):
        """Log debug message with event context"""
        extra = _extract_event_properties(event)
        self.logger.debug(message, extra=extra)
    
    def log_info(self, message: str, event):
        """Log info message with event context"""
        extra = _extract_event_properties(event)
        self.logger.info(message, extra=extra)
    
    def log_warning(self, message: str, event):
        """Log warning message with event context"""
        extra = _extract_event_properties(event)
        self.logger.warning(message, extra=extra)
    
    def log_error(self, message: str, event):
        """Log error message with event context"""
        extra = _extract_event_properties(event)
        self.logger.error(message, extra=extra)