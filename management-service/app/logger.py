"""
Logging configuration for the Management Service
"""
import logging
import sys
import os
import gzip
import shutil
from logging.handlers import TimedRotatingFileHandler
from typing import Optional


class CompressingTimedRotatingFileHandler(TimedRotatingFileHandler):
    """TimedRotatingFileHandler that compresses rotated files"""
    
    def doRollover(self):
        """Override to add compression after rotation"""
        # Perform the standard rollover
        super().doRollover()
        
        # Compress the rotated file
        # The rotated file will have a timestamp suffix
        # Find the most recent rotated file
        dir_name, base_name = os.path.split(self.baseFilename)
        
        try:
            file_names = os.listdir(dir_name)
            
            for file_name in file_names:
                if file_name.startswith(base_name) and not file_name.endswith('.gz') and file_name != base_name:
                    full_path = os.path.join(dir_name, file_name)
                    # Compress the file
                    with open(full_path, 'rb') as f_in:
                        with gzip.open(f'{full_path}.gz', 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    # Remove the uncompressed file
                    os.remove(full_path)
        except Exception as e:
            # Log compression errors but don't fail the rollover
            print(f"Error during log compression: {e}", file=sys.stderr)


def setup_logger(name: Optional[str] = None, level: str = "INFO") -> logging.Logger:
    """
    Set up structured logging for the Management Service
    
    Args:
        name: Logger name (defaults to __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers if logger already configured
    if logger.handlers:
        return logger
    
    # Set log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler with daily rotation and compression
    log_dir = '/app/logs'
    os.makedirs(log_dir, exist_ok=True)
    
    file_handler = CompressingTimedRotatingFileHandler(
        filename=os.path.join(log_dir, 'management-service.log'),
        when='midnight',
        interval=1,
        backupCount=365,  # Keep 365 days of logs
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def configure_root_logger(level: str = "INFO"):
    """Configure the root logger with file and console handlers"""
    # Get root logger
    root_logger = logging.getLogger()
    
    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Set log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler with daily rotation and compression
    log_dir = '/app/logs'
    os.makedirs(log_dir, exist_ok=True)
    
    file_handler = CompressingTimedRotatingFileHandler(
        filename=os.path.join(log_dir, 'management-service.log'),
        when='midnight',
        interval=1,
        backupCount=365,  # Keep 365 days of logs
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)