import asyncio
import logging
from typing import Callable, Any, Optional, Union
from app.config import RetryConfig
from app.logger import AppLogger

app_logger = AppLogger(__name__)

async def retry_with_config(
    func: Callable,
    retry_config: RetryConfig,
    operation_name: str,
    *args,
    **kwargs
) -> Any:
    """
    Generic retry utility that uses RetryConfig settings.
    
    Args:
        func: The async function to retry
        retry_config: RetryConfig object with retry parameters
        operation_name: Name for logging purposes
        *args, **kwargs: Arguments to pass to func
        
    Returns:
        Result of successful function call
        
    Raises:
        Exception: The last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(retry_config.max_retries + 1):  # +1 because range is exclusive
        try:
            if attempt > 0:
                app_logger.log_info(f"{operation_name}: Attempt {attempt + 1}/{retry_config.max_retries + 1}")
            
            result = await func(*args, **kwargs)
            
            if attempt > 0:
                app_logger.log_info(f"{operation_name}: Succeeded on attempt {attempt + 1}")
            
            return result
            
        except Exception as e:
            last_exception = e
            
            if attempt < retry_config.max_retries:
                delay = retry_config.delay
                app_logger.log_warning(
                    f"{operation_name}: Attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {delay} seconds..."
                )
                await asyncio.sleep(delay)
            else:
                app_logger.log_error(f"{operation_name}: All {retry_config.max_retries + 1} attempts failed")
    
    raise last_exception

