import asyncio
import random
import logging
from typing import Callable, Any, Optional, Union
from app.config import RetryConfig

logger = logging.getLogger(__name__)

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
                logger.info(f"{operation_name}: Attempt {attempt + 1}/{retry_config.max_retries + 1}")
            
            result = await func(*args, **kwargs)
            
            if attempt > 0:
                logger.info(f"{operation_name}: Succeeded on attempt {attempt + 1}")
            
            return result
            
        except Exception as e:
            last_exception = e
            
            if attempt < retry_config.max_retries:
                delay = _calculate_delay(attempt, retry_config)
                logger.warning(
                    f"{operation_name}: Attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"{operation_name}: All {retry_config.max_retries + 1} attempts failed")
    
    raise last_exception

def _calculate_delay(attempt: int, retry_config: RetryConfig) -> float:
    """
    Calculate delay for next retry attempt using exponential backoff with optional jitter.
    
    Args:
        attempt: Current attempt number (0-based)
        retry_config: RetryConfig object with delay parameters
        
    Returns:
        Delay in seconds
    """
    # Exponential backoff: base_delay * (backoff_multiplier ^ attempt)
    delay = retry_config.base_delay * (retry_config.backoff_multiplier ** attempt)
    
    # Cap at max_delay
    delay = min(delay, retry_config.max_delay)
    
    # Add jitter if enabled (randomize ±20% of delay)
    if retry_config.jitter:
        jitter_range = delay * 0.2
        delay += random.uniform(-jitter_range, jitter_range)
        delay = max(0.1, delay)  # Ensure minimum delay of 0.1 seconds
    
    return delay