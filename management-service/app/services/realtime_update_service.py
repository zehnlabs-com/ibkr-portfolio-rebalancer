"""
Real-time Update Service for Dashboard Updates

This service subscribes to Redis pub/sub channels for account data updates
and broadcasts them to WebSocket clients for real-time dashboard updates.
"""
import json
import asyncio
import logging
from typing import Optional
from app.services.redis_data_service import RedisDataService
from app.logger import setup_logger

logger = setup_logger(__name__)


class RealtimeUpdateService:
    """Service for handling real-time dashboard updates via Redis pub/sub"""
    
    def __init__(self, redis_data_service: RedisDataService, websocket_manager):
        self.redis_data_service = redis_data_service
        self.websocket_manager = websocket_manager
        self._subscriber_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def start(self) -> None:
        """Start the Redis pub/sub subscriber"""
        if self._running:
            logger.warning("Real-time update service already running")
            return
            
        try:
            self._running = True
            
            # Start the subscriber task
            self._subscriber_task = asyncio.create_task(self._subscriber_loop())
            
            logger.info("Real-time update service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start real-time update service: {e}")
            await self.stop()
            raise
            
    async def stop(self) -> None:
        """Stop the Redis pub/sub subscriber"""
        self._running = False
        
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
                
        logger.info("Real-time update service stopped")
        
    async def _subscriber_loop(self) -> None:
        """Main subscriber loop for Redis pub/sub messages"""
        try:
            # Ensure Redis connection and get client directly
            self.redis_data_service._ensure_connected()
            redis_client = self.redis_data_service.redis_client

            pubsub = redis_client.pubsub()
            await pubsub.subscribe("dashboard_updates")
            logger.info("Successfully subscribed to dashboard_updates channel")
            
            async for message in pubsub.listen():
                if not self._running:
                    break
                    
                if message['type'] != 'message':
                    continue
                    
                try:
                    import json
                    data = json.loads(message['data'])
                    
                    # Handle different message types
                    message_type = data.get('type', 'unknown')
                    
                    if message_type == 'account_data_updated':
                        await self._handle_account_update(data)
                    elif message_type == 'dashboard_summary_updated':
                        await self._handle_summary_update(data)
                    else:
                        # Forward unknown messages as-is
                        await self.websocket_manager.broadcast({
                            "type": "dashboard_update",
                            "data": data
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing dashboard update: {e}")
                    
        except Exception as e:
            logger.error(f"Error in subscriber loop: {e}")
    
    async def _handle_account_update(self, message: dict) -> None:
        """Handle individual account data updates"""
        try:
            account_id = message.get('account_id')
            if not account_id:
                logger.warning("Account update message missing account_id")
                return
            
            # Get the updated account data
            account_data = await self.redis_data_service.get_account_data(account_id)
            if account_data:
                # Broadcast account update to WebSocket clients
                await self.websocket_manager.broadcast({
                    "type": "account_update",
                    "data": {
                        "account_id": account_id,
                        "account_data": account_data
                    }
                })
                
                logger.debug(f"Broadcasted account update for {account_id}")
                
        except Exception as e:
            logger.error(f"Failed to handle account update: {e}")
    
    async def _handle_summary_update(self, message: dict) -> None:
        """Handle dashboard summary updates"""
        try:
            # Broadcast summary update to WebSocket clients
            await self.websocket_manager.broadcast({
                "type": "summary_update", 
                "data": message.get('summary', {})
            })
            
            logger.debug("Broadcasted summary update")
            
        except Exception as e:
            logger.error(f"Failed to handle summary update: {e}")
    
    async def get_current_dashboard_data(self) -> dict:
        """Get current dashboard data for newly connected clients"""
        try:
            # Get all account data
            accounts_data = await self.redis_data_service.get_all_accounts_data()
            
            return {
                "type": "dashboard_initial",
                "data": {
                    "accounts": accounts_data,
                    "timestamp": asyncio.get_event_loop().time()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get current dashboard data: {e}")
            return {
                "type": "dashboard_initial",
                "data": {
                    "accounts": [],
                    "timestamp": asyncio.get_event_loop().time(),
                    "error": str(e)
                }
            }