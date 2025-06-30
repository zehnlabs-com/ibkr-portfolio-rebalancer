import asyncio
import json
from typing import Optional
from ably import AblyRealtime
from app.config import AccountConfig
from app.logger import setup_logger

logger = setup_logger(__name__)

class AblyService:
    def __init__(self, account_config: AccountConfig, rebalancer_service):
        self.account_config = account_config
        self.rebalancer_service = rebalancer_service
        self.ably: Optional[AblyRealtime] = None
        self.channel = None
        self.running = False
    
    async def start(self):
        if not self.account_config.notification.channel:
            logger.warning(f"No notification channel configured for account {self.account_config.account_id}")
            return
        
        try:
            # Use the global API key from config
            from app.config import config
            api_key = config.realtime_api_key
            
            if not api_key:
                logger.error(f"No REALTIME_API_KEY configured for channel: {self.account_config.notification.channel}")
                return
            
            # Create Ably realtime client
            self.ably = AblyRealtime(api_key)
            
            # Use the channel name directly from config
            channel_name = self.account_config.notification.channel
            logger.info(f"Connecting to Ably channel: {channel_name}")
            
            # Get the channel
            self.channel = self.ably.channels.get(channel_name)
            
            # Subscribe to all messages on the channel - this is actually async!
            await self.channel.subscribe(self._handle_rebalance_event)
            
            self.running = True
            logger.info(f"Started Ably subscription for account {self.account_config.account_id} on channel {channel_name}")
            
            # Connection state logging
            def on_connection_state_change(state_change):
                logger.info(f"Ably connection state changed to: {state_change.current}")
            
            self.ably.connection.on('connected', lambda: logger.info("Ably connection established"))
            self.ably.connection.on('failed', lambda: logger.error("Ably connection failed"))
            self.ably.connection.on('disconnected', lambda: logger.warning("Ably connection lost"))
            
        except Exception as e:
            logger.error(f"Failed to start Ably service: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def stop(self):
        self.running = False
        
        if self.channel:
            try:
                # Unsubscribe is also async
                await self.channel.unsubscribe()
                logger.info(f"Unsubscribed from Ably channel for account {self.account_config.account_id}")
            except Exception as e:
                logger.error(f"Error unsubscribing from Ably channel: {e}")
        
        if self.ably:
            try:
                # Close is synchronous, not async
                self.ably.close()
                logger.info(f"Closed Ably connection for account {self.account_config.account_id}")
            except Exception as e:
                logger.error(f"Error closing Ably connection: {e}")
    
    async def _handle_rebalance_event(self, message):
        try:
            logger.info(f"Received rebalance event for account {self.account_config.account_id}: {message.data}")
            
            # Parse the message payload
            payload = {}
            if message.data:
                try:
                    import json
                    if isinstance(message.data, str):
                        payload = json.loads(message.data)
                    elif isinstance(message.data, dict):
                        payload = message.data
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Invalid JSON payload, defaulting to dry run: {message.data}")
            
            # Determine execution mode from payload
            execution_mode = payload.get("execution", "dry_run")
            is_live_execution = execution_mode == "rebalance"
            
            if is_live_execution:
                logger.info(f"Live rebalance triggered for account {self.account_config.account_id}")
                await self.rebalancer_service.rebalance_account(self.account_config, dry_run=False)
            else:
                logger.info(f"Dry run rebalance triggered for account {self.account_config.account_id} (execution: {execution_mode})")
                await self.rebalancer_service.rebalance_account(self.account_config, dry_run=True)
            
        except Exception as e:
            logger.error(f"Error handling rebalance event: {e}")
    
