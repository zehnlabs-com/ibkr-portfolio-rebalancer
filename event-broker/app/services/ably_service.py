"""
Enhanced Ably service for event subscription and Redis queue integration
"""
import asyncio
import json
import yaml
from typing import Dict, List, Optional, Any
from ably import AblyRealtime
from app.logger import setup_logger
from app.config import config
from app.services.queue_service import QueueService

logger = setup_logger(__name__, level=config.LOG_LEVEL)


class AccountConfig:
    """Account configuration model"""
    
    def __init__(self, data: Dict[str, Any]):
        self.account_id = data.get('account_id')
        self.strategy_name = data.get('notification', {}).get('channel')
        self.type = data.get('type')
        # Add rebalancing configuration
        rebalancing_data = data.get('rebalancing', {})
        self.cash_reserve_percent = rebalancing_data.get('cash_reserve_percent', rebalancing_data.get('equity_reserve_percentage', 0.0))


class AblyEventSubscriber:
    """Enhanced Ably service that subscribes to events and enqueues to Redis"""
    
    def __init__(self):
        self.api_key = config.REALTIME_API_KEY
        self.ably: Optional[AblyRealtime] = None
        self.queue_service = QueueService()
        self.accounts: List[AccountConfig] = []
        self.channels: Dict[str, Any] = {}
        self.running = False
        
    async def start(self):
        """Start the Ably service and subscribe to all configured channels"""
        if not self.api_key:
            logger.error("No REALTIME_API_KEY configured")
            return
            
        try:
            
            # Load account configurations
            await self._load_accounts()
            
            if not self.accounts:
                logger.warning("No accounts configured for event subscription")
                return
            
            # Create Ably realtime client
            self.ably = AblyRealtime(self.api_key)
            
            # Set up connection state logging
            self._setup_connection_monitoring()
            
            # Subscribe to channels for all accounts
            await self._subscribe_to_channels()
            
            # Verify Redis connectivity
            await self._verify_services_health()
            
            self.running = True
            logger.info(f"Started Ably Event Broker with {len(self.accounts)} accounts")
            
        except Exception as e:
            logger.error(f"Failed to start Ably Event Broker: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    async def stop(self):
        """Stop the Ably service and clean up resources"""
        self.running = False
        
        # Unsubscribe from all channels
        for channel_name, channel in self.channels.items():
            try:
                await channel.unsubscribe()
                logger.info(f"Unsubscribed from channel: {channel_name}")
            except Exception as e:
                logger.error(f"Error unsubscribing from channel {channel_name}: {e}")
        
        # Close Ably connection
        if self.ably:
            try:
                self.ably.close()
                logger.info("Closed Ably connection")
            except Exception as e:
                logger.error(f"Error closing Ably connection: {e}")
        
        
        logger.info("Stopped Ably Event Broker")
    
    async def _load_accounts(self):
        """Load account configurations from YAML file"""
        try:
            with open(config.ACCOUNTS_FILE, 'r') as f:
                yaml_data = yaml.safe_load(f)
            
            # Extract accounts array from new YAML structure
            accounts_data = yaml_data.get('accounts', [])
            
            self.accounts = []
            trading_mode = config.TRADING_MODE
            
            # accounts_data is a list of account configurations
            for account_data in accounts_data:
                account = AccountConfig(account_data)
                if account.account_id and account.strategy_name and account.type == trading_mode:
                    self.accounts.append(account)
                    logger.debug(f"Loaded account: {account.account_id} -> {account.strategy_name}")
                elif not account.account_id:
                    logger.warning(f"Skipping account configuration: missing account_id")
                elif not account.strategy_name:
                    logger.warning(f"Skipping account {account.account_id}: missing strategy channel")
                elif account.type != trading_mode:
                    # Normal filtering - don't log anything
                    pass
                else:
                    logger.warning(f"Skipping account {account.account_id}: invalid configuration")
            
            logger.info(f"Loaded {len(self.accounts)} account configurations ({trading_mode})")
            
        except Exception as e:
            logger.error(f"Failed to load account configurations: {e}")
            raise
    
    async def _subscribe_to_channels(self):
        """Subscribe to Ably channels for all configured accounts"""
        for account in self.accounts:
            try:
                channel_name = account.strategy_name
                logger.info(f"Subscribing to channel: {channel_name} for account: {account.account_id}")
                
                # Get the channel
                channel = self.ably.channels.get(channel_name)
                
                # Subscribe to all messages on the channel
                def create_message_handler(account_config):
                    def message_handler(message, *args, **kwargs):
                        asyncio.create_task(self._handle_event(message, account_config))
                    return message_handler
                
                await channel.subscribe(create_message_handler(account))
                
                # Store channel reference
                self.channels[channel_name] = channel
                
                logger.info(f"Successfully subscribed to channel: {channel_name}")
                
            except Exception as e:
                logger.error(f"Failed to subscribe to channel {account.strategy_name}: {e}")
    
    async def _handle_event(self, message, account: AccountConfig):
        """
        Handle incoming events by enqueuing to Redis
        
        Args:
            message: Ably message object
            account: Account configuration
        """
        event_id = None
        try:
            logger.info(f"Received event for account {account.account_id}: {message.data}")
            
            # Parse the message payload
            payload = {}
            if message.data:
                try:
                    if isinstance(message.data, str):
                        payload = json.loads(message.data)
                    elif isinstance(message.data, dict):
                        payload = message.data
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Invalid JSON payload, using empty payload: {message.data}")
                    payload = {"raw_data": str(message.data)}
            
            # Get the action from payload
            action = payload.get("exec")
            
            if not action:
                logger.error(f"No action specified in payload for account {account.account_id}: {payload}")
                return
            
            # Log the action being taken
            logger.info(f"Exec '{action}' event received for account {account.account_id}")
            
            enhanced_payload = {
                **payload,
                "account_id": account.account_id,
                "strategy_name": account.strategy_name,
                "cash_reserve_percent": account.cash_reserve_percent
            }
            
            # Enqueue to Redis (with deduplication)
            event_id = await self.queue_service.enqueue_event(account.account_id, enhanced_payload)
            
            if event_id:
                
                logger.info(f"Event enqueued successfully", extra={
                    'event_id': event_id,
                    'account_id': account.account_id,
                    'exec': action
                })
            else:
                logger.info(f"Event not enqueued - account {account.account_id} already queued")
            
        except Exception as e:
            logger.error(f"Error handling event for account {account.account_id}: {e}")
    
    async def _verify_services_health(self):
        """Verify that Redis is accessible"""
        try:
            # Check Redis connectivity
            if self.queue_service.is_connected():
                logger.info("Redis connectivity check passed")
            else:
                logger.warning("Redis connectivity check failed")
                
        except Exception as e:
            logger.error(f"Failed to verify services health: {e}")
            # Don't raise here - we want to continue even if health check fails initially
    
    def _setup_connection_monitoring(self):
        """Set up Ably connection state monitoring"""
        def on_connected(state_change, *args, **kwargs):
            logger.info("Ably connection established")
        
        def on_failed(state_change, *args, **kwargs):
            logger.error("Ably connection failed")
        
        def on_disconnected(state_change, *args, **kwargs):
            logger.warning("Ably connection lost")
        
        def on_suspended(state_change, *args, **kwargs):
            logger.warning("Ably connection suspended")
        
        def on_closing(state_change, *args, **kwargs):
            logger.info("Ably connection closing")
        
        def on_closed(state_change, *args, **kwargs):
            logger.info("Ably connection closed")
        
        # Set up connection event handlers
        self.ably.connection.on('connected', on_connected)
        self.ably.connection.on('failed', on_failed)
        self.ably.connection.on('disconnected', on_disconnected)
        self.ably.connection.on('suspended', on_suspended)
        self.ably.connection.on('closing', on_closing)
        self.ably.connection.on('closed', on_closed)
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current status of the event broker"""
        status = {
            "running": self.running,
            "accounts_count": len(self.accounts),
            "channels_count": len(self.channels),
            "ably_connected": self.ably.connection.state == 'connected' if self.ably else False,
            "redis_connected": False,
            "queue_length": 0,
            "queued_accounts": 0
        }
        
        try:
            status["redis_connected"] = self.queue_service.is_connected()
            status["queue_length"] = self.queue_service.get_queue_length()
            status["queued_accounts"] = len(self.queue_service.get_queued_accounts())
        except:
            pass
            
        
        return status