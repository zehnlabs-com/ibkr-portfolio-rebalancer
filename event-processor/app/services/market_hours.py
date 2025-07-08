"""
Market Hours Service for Event Processor
"""
import asyncio
from datetime import datetime, time
from typing import Optional
from ib_insync import IB, Stock
from app.config import config
from app.logger import setup_logger

logger = setup_logger(__name__)


class MarketHoursService:
    """Service for determining market hours and trading status using SPY as reference"""
    
    def __init__(self, ibkr_client=None):
        self.ibkr_client = ibkr_client
        self._market_open_time = time(9, 30)  # 9:30 AM EST fallback
        self._market_close_time = time(16, 0)  # 4:00 PM EST fallback
        
    async def is_market_open(self) -> bool:
        """
        Check if markets are currently open
        
        For now, uses simple time-based logic. In production, this could be
        enhanced to use IBKR contract details or external market calendar APIs.
        
        Returns:
            bool: True if markets are open
        """
        try:
            current_time = datetime.now().time()
            current_weekday = datetime.now().weekday()
            
            # Simple check: Monday-Friday, 9:30 AM - 4:00 PM EST
            # TODO: Enhance with holiday calendar and actual market hours from IBKR
            is_weekday = current_weekday < 5  # Monday = 0, Friday = 4
            is_market_hours = self._market_open_time <= current_time <= self._market_close_time
            
            market_open = is_weekday and is_market_hours
            
            logger.debug(f"Market status check", extra={
                'current_time': current_time.isoformat(),
                'current_weekday': current_weekday,
                'is_weekday': is_weekday,
                'is_market_hours': is_market_hours,
                'market_open': market_open
            })
            
            return market_open
            
        except Exception as e:
            logger.error(f"Failed to check market hours: {e}")
            # In case of error, assume markets are closed for safety
            return False
    
    async def get_market_close_time(self) -> time:
        """
        Get market close time
        
        Returns:
            time: Market close time (4:00 PM EST)
        """
        return self._market_close_time
    
    async def get_market_open_time(self) -> time:
        """
        Get market open time
        
        Returns:
            time: Market open time (9:30 AM EST)
        """
        return self._market_open_time
    
    async def time_until_close(self) -> Optional[int]:
        """
        Get time until market close in minutes
        
        Returns:
            int: Minutes until market close, None if market is closed
        """
        try:
            if not await self.is_market_open():
                return None
            
            current_time = datetime.now().time()
            current_datetime = datetime.combine(datetime.today(), current_time)
            close_datetime = datetime.combine(datetime.today(), self._market_close_time)
            
            time_diff = close_datetime - current_datetime
            minutes_until_close = int(time_diff.total_seconds() / 60)
            
            logger.debug(f"Time until market close: {minutes_until_close} minutes")
            
            return max(0, minutes_until_close)
            
        except Exception as e:
            logger.error(f"Failed to calculate time until close: {e}")
            return None
    
    async def should_use_moc_orders(self) -> bool:
        """
        Determine if Market on Close (MOC) orders should be used
        
        MOC orders should be used within the configured buffer time before market close
        
        Returns:
            bool: True if MOC orders should be used
        """
        try:
            time_until_close = await self.time_until_close()
            
            if time_until_close is None:
                # Market is closed, no orders should be placed
                return False
            
            buffer_minutes = config.processing.market_hours_buffer
            should_use_moc = time_until_close <= buffer_minutes
            
            logger.debug(f"MOC order check", extra={
                'time_until_close': time_until_close,
                'buffer_minutes': buffer_minutes,
                'should_use_moc': should_use_moc
            })
            
            return should_use_moc
            
        except Exception as e:
            logger.error(f"Failed to determine MOC order usage: {e}")
            return False
    
    async def get_order_type(self) -> str:
        """
        Get appropriate order type based on market timing
        
        Returns:
            str: "MOC" if near market close, "MKT" otherwise
        """
        try:
            if await self.should_use_moc_orders():
                return "MOC"
            else:
                return "MKT"
        except Exception as e:
            logger.error(f"Failed to determine order type: {e}")
            return "MKT"  # Default to market orders