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
from app.services.event_service import EventService

logger = setup_logger(__name__, level=config.LOG_LEVEL)


class AccountConfig:
    """Account configuration model"""
    
    def __init__(self, data: Dict[str, Any]):
        self.account_id = data.get('account_id')
        self.notification_channel = data.get('notification', {}).get('channel')
        self.allocations_url = data.get('allocations', {}).get('url')


class AblyEventSubscriber:
    """Enhanced Ably service that subscribes to events and enqueues to Redis"""
    
    def __init__(self):
        self.api_key = config.REALTIME_API_KEY
        self.ably: Optional[AblyRealtime] = None
        self.queue_service = QueueService()
        self.event_service = EventService()
        self.accounts: List[AccountConfig] = []
        self.channels: Dict[str, Any] = {}
        self.running = False
        
    async def start(self):
        """Start the Ably service and subscribe to all configured channels"""
        if not self.api_key:
            logger.error("No REALTIME_API_KEY configured")
            return
            
        try:
            # Initialize database connection pool
            await self.event_service.init_connection_pool()
            
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
            
            # Verify Redis and PostgreSQL connectivity
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
        
        # Close database connection pool
        await self.event_service.close_connection_pool()
        
        logger.info("Stopped Ably Event Broker")
    
    async def _load_accounts(self):
        """Load account configurations from YAML file"""
        try:
            with open(config.ACCOUNTS_FILE, 'r') as f:
                accounts_data = yaml.safe_load(f)
            
            self.accounts = []
            # accounts_data is a list of account configurations
            for account_data in accounts_data:
                account = AccountConfig(account_data)
                if account.account_id and account.notification_channel:
                    self.accounts.append(account)
                    logger.debug(f"Loaded account: {account.account_id} -> {account.notification_channel}")
                else:
                    logger.warning(f"Invalid account configuration: {account_data}")
            
            logger.info(f"Loaded {len(self.accounts)} account configurations")
            
        except Exception as e:
            logger.error(f"Failed to load account configurations: {e}")
            raise
    
    async def _subscribe_to_channels(self):
        """Subscribe to Ably channels for all configured accounts"""
        for account in self.accounts:
            try:
                channel_name = account.notification_channel
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
                logger.error(f"Failed to subscribe to channel {account.notification_channel}: {e}")
    
    async def _handle_event(self, message, account: AccountConfig):
        """
        Handle incoming events by enqueuing to Redis and tracking in PostgreSQL
        
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
            
            # Enqueue to Redis (with deduplication)
            event_id = await self.queue_service.enqueue_event(account.account_id, payload)
            
            if event_id:
                # Track event in PostgreSQL
                await self.event_service.create_event(event_id, account.account_id, payload)
                
                logger.info(f"Event enqueued successfully", extra={
                    'event_id': event_id,
                    'account_id': account.account_id,
                    'exec': action
                })
            else:
                logger.info(f"Event not enqueued - account {account.account_id} already queued")
            
        except Exception as e:
            logger.error(f"Error handling event for account {account.account_id}: {e}")
            if event_id:
                try:
                    await self.event_service.update_event_status(event_id, 'failed', str(e))
                except:
                    pass  # Don't fail on logging failure
    
    async def _verify_services_health(self):
        """Verify that Redis and PostgreSQL are accessible"""
        try:
            # Check Redis connectivity
            if self.queue_service.is_connected():
                logger.info("Redis connectivity check passed")
            else:
                logger.warning("Redis connectivity check failed")
                
            # Check PostgreSQL connectivity
            if await self.event_service.is_connected():
                logger.info("PostgreSQL connectivity check passed")
            else:
                logger.warning("PostgreSQL connectivity check failed")
                
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
            "postgresql_connected": False,
            "queue_length": 0,
            "queued_accounts": 0
        }
        
        try:
            status["redis_connected"] = self.queue_service.is_connected()
            status["queue_length"] = self.queue_service.get_queue_length()
            status["queued_accounts"] = len(self.queue_service.get_queued_accounts())
        except:
            pass
            
        try:
            status["postgresql_connected"] = await self.event_service.is_connected()
        except:
            pass
        
        return status