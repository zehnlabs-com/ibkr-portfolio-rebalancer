import logging
import sys
import json
from typing import Dict, Any
from app.config import config

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging with event_id support"""
    
    def format(self, record):
        # Start with basic log structure
        log_data = {
            'timestamp': self.formatTime(record),
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

def log_with_event(logger: logging.Logger, level: str, message: str, event_id: str = None, account_id: str = None, **kwargs):
    """Helper function to log with event_id and account_id"""
    extra = kwargs.copy()
    if event_id:
        extra['event_id'] = event_id
    if account_id:
        extra['account_id'] = account_id
    
    log_method = getattr(logger, level.lower())
    log_method(message, extra=extra)