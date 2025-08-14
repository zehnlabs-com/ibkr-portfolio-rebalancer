"""
Real-time Update Service for Dashboard Updates

This service subscribes to Redis pub/sub channels for account data updates
and broadcasts them to WebSocket clients for real-time dashboard updates.
"""
import json
import asyncio
import logging
from typing import Optional
import redis.asyncio as redis

from app.logger import setup_logger

logger = setup_logger(__name__)


class RealtimeUpdateService:
    """Service for handling real-time dashboard updates via Redis pub/sub"""
    
    def __init__(self, redis_url: str, websocket_manager):
        self.redis_url = redis_url
        self.websocket_manager = websocket_manager
        self.redis_subscriber: Optional[redis.Redis] = None
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self._subscriber_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def start(self) -> None:
        """Start the Redis pub/sub subscriber"""
        if self._running:
            logger.warning("Real-time update service already running")
            return
            
        try:
            # Create separate Redis connections for subscriber and data fetching
            self.redis_subscriber = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            
            # Test connections
            await self.redis_subscriber.ping()
            await self.redis_client.ping()
            
            # Set up pub/sub
            self.pubsub = self.redis_subscriber.pubsub()
            await self.pubsub.subscribe("dashboard_updates")
            
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
                
        if self.pubsub:
            await self.pubsub.unsubscribe("dashboard_updates")
            await self.pubsub.close()
            
        if self.redis_subscriber:
            await self.redis_subscriber.close()
            
        if self.redis_client:
            await self.redis_client.close()
            
        logger.info("Real-time update service stopped")
        
    async def _subscriber_loop(self) -> None:
        """Main subscriber loop that listens for Redis pub/sub messages"""
        while self._running:
            try:
                # Listen for messages with timeout to allow clean shutdown
                message = await asyncio.wait_for(
                    self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1),
                    timeout=2.0
                )
                
                if message and message['type'] == 'message':
                    await self._handle_message(message)
                    
            except asyncio.TimeoutError:
                # Normal timeout - continue loop
                continue
            except Exception as e:
                logger.error(f"Error in subscriber loop: {e}")
                await asyncio.sleep(1)
                
    async def _handle_message(self, message: dict) -> None:
        """Handle incoming Redis pub/sub messages"""
        try:
            data = json.loads(message['data'])
            message_type = data.get('type')
            
            logger.info(f"Received message: {message_type}")
            
            if message_type == "account_data_updated":
                await self._handle_account_data_updated(data)
            elif message_type == "dashboard_summary_updated":
                await self._handle_dashboard_summary_updated(data)
            else:
                logger.debug(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Failed to handle message: {e}")
            
    async def _handle_account_data_updated(self, data: dict) -> None:
        """Handle account data update notifications"""
        try:
            account_id = data.get('account_id')
            if not account_id:
                logger.warning("Account data update message missing account_id")
                return
                
            # Fetch updated account data from Redis
            account_data_str = await self.redis_client.get(f"account_data:{account_id}")
            if not account_data_str:
                logger.warning(f"No account data found for {account_id}")
                return
                
            account_data = json.loads(account_data_str)
            
            # Send account update to WebSocket clients
            await self.websocket_manager.send_account_update(account_data)
            
            logger.info(f"Broadcast account update for {account_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle account data update: {e}")
            
    async def _handle_dashboard_summary_updated(self, data: dict) -> None:
        """Handle dashboard summary update notifications"""
        try:
            # Get all account data from Redis and send dashboard summary
            from app.container import container
            dashboard_handlers = container.dashboard_handlers
            
            # Get all accounts data
            accounts_data = await dashboard_handlers._get_all_accounts_data()
            
            if not accounts_data:
                logger.warning("No accounts data found for dashboard summary")
                return
            
            # Calculate dashboard summary data
            total_value = sum(account.current_value for account in accounts_data)
            total_pnl = sum(account.todays_pnl for account in accounts_data)
            
            # Safe percentage calculation
            denominator = total_value - total_pnl
            if denominator > 0:
                total_pnl_percent = (total_pnl / denominator) * 100
            else:
                total_pnl_percent = 0.0
            
            total_positions = sum(account.positions_count for account in accounts_data)
            
            dashboard_data = {
                "total_value": total_value,
                "total_pnl": total_pnl,
                "total_pnl_percent": total_pnl_percent,
                "total_positions": total_positions,
                "accounts_count": len(accounts_data),
                "accounts": [
                    {
                        "account_id": account.account_id,
                        "strategy_name": account.strategy_name,
                        "current_value": account.current_value,
                        "todays_pnl": account.todays_pnl,
                        "todays_pnl_percent": account.todays_pnl_percent,
                        "positions_count": account.positions_count,
                        "last_update": account.last_update.isoformat()
                    } for account in accounts_data
                ],
                "last_update": accounts_data[0].last_update.isoformat() if accounts_data else None
            }
            
            # Send dashboard update to WebSocket clients
            dashboard_message = {
                "type": "dashboard",
                "action": "update",
                "data": dashboard_data
            }
            await self.websocket_manager.broadcast(dashboard_message)
            
            # Also send account list update
            account_message = {
                "type": "account",
                "action": "update",
                "data": [
                    {
                        "account_id": account.account_id,
                        "strategy_name": account.strategy_name,
                        "current_value": account.current_value,
                        "last_close_netliq": account.last_close_netliq,
                        "todays_pnl": account.todays_pnl,
                        "todays_pnl_percent": account.todays_pnl_percent,
                        "total_unrealized_pnl": account.total_unrealized_pnl,
                        "positions_count": account.positions_count,
                        "last_update": account.last_update.isoformat(),
                        "last_rebalanced_on": account.last_rebalanced_on.isoformat() if account.last_rebalanced_on else None
                    } for account in accounts_data
                ]
            }
            await self.websocket_manager.broadcast(account_message)
            
            logger.info(f"Broadcast dashboard summary update with {len(accounts_data)} accounts")
            
        except Exception as e:
            logger.error(f"Failed to handle dashboard summary update: {e}")