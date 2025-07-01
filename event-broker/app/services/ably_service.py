"""
Enhanced Ably service for event subscription and HTTP communication
"""
import asyncio
import json
import yaml
from typing import Dict, List, Optional, Any
from ably import AblyRealtime
from app.logger import setup_logger
from app.config import config
from app.services.rebalancer_client import RebalancerClient

logger = setup_logger(__name__)


class AccountConfig:
    """Account configuration model"""
    
    def __init__(self, data: Dict[str, Any]):
        self.account_id = data.get('account_id')
        self.notification_channel = data.get('notification', {}).get('channel')
        self.allocations_url = data.get('allocations', {}).get('url')


class AblyEventSubscriber:
    """Enhanced Ably service that subscribes to events and triggers rebalancing via HTTP"""
    
    def __init__(self):
        self.api_key = config.REALTIME_API_KEY
        self.ably: Optional[AblyRealtime] = None
        self.rebalancer_client = RebalancerClient()
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
            
            # Verify rebalancer API is healthy
            await self._verify_rebalancer_health()
            
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
        
        # Close HTTP client
        await self.rebalancer_client.close()
        
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
                await channel.subscribe(lambda message, acc=account: asyncio.create_task(
                    self._handle_rebalance_event(message, acc)
                ))
                
                # Store channel reference
                self.channels[channel_name] = channel
                
                logger.info(f"Successfully subscribed to channel: {channel_name}")
                
            except Exception as e:
                logger.error(f"Failed to subscribe to channel {account.notification_channel}: {e}")
    
    async def _handle_rebalance_event(self, message, account: AccountConfig):
        """
        Handle incoming rebalance events by triggering HTTP calls to rebalancer API
        
        Args:
            message: Ably message object
            account: Account configuration
        """
        try:
            logger.info(f"Received rebalance event for account {account.account_id}: {message.data}")
            
            # Parse the message payload
            payload = {}
            if message.data:
                try:
                    if isinstance(message.data, str):
                        payload = json.loads(message.data)
                    elif isinstance(message.data, dict):
                        payload = message.data
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Invalid JSON payload, defaulting to dry run: {message.data}")
            
            # Determine execution mode from payload
            execution_mode = payload.get("execution", "dry_run")
            
            # Validate execution mode
            if execution_mode not in ["dry_run", "rebalance"]:
                logger.warning(f"Invalid execution mode '{execution_mode}', defaulting to dry_run")
                execution_mode = "dry_run"
            
            # Log the action being taken
            action_type = "Live rebalance" if execution_mode == "rebalance" else "Dry run rebalance"
            logger.info(f"{action_type} triggered for account {account.account_id}")
            
            # Make HTTP call to rebalancer API
            try:
                response = await self.rebalancer_client.trigger_rebalance(
                    account_id=account.account_id,
                    execution_mode=execution_mode
                )
                
                # Log the results
                orders = response.get('orders', [])
                status = response.get('status', 'unknown')
                message_text = response.get('message', '')
                
                logger.info(f"Rebalance completed for account {account.account_id}: "
                          f"status={status}, orders={len(orders)}, message={message_text}")
                
                # Log order details in debug mode
                for order in orders:
                    logger.debug(f"Order: {order.get('action')} {order.get('quantity')} "
                                f"{order.get('symbol')} (${order.get('market_value', 0):.2f})")
                
            except Exception as e:
                logger.error(f"Failed to trigger rebalance for account {account.account_id}: {e}")
                # Don't re-raise here - we want to continue processing other events
            
        except Exception as e:
            logger.error(f"Error handling rebalance event for account {account.account_id}: {e}")
    
    async def _verify_rebalancer_health(self):
        """Verify that the rebalancer API is healthy and accessible"""
        try:
            is_healthy = await self.rebalancer_client.health_check()
            if is_healthy:
                logger.info("Rebalancer API health check passed")
            else:
                logger.warning("Rebalancer API health check failed - service may not be ready")
        except Exception as e:
            logger.error(f"Failed to verify rebalancer API health: {e}")
            # Don't raise here - we want to continue even if health check fails initially
    
    def _setup_connection_monitoring(self):
        """Set up Ably connection state monitoring"""
        def on_connected():
            logger.info("Ably connection established")
        
        def on_failed():
            logger.error("Ably connection failed")
        
        def on_disconnected():
            logger.warning("Ably connection lost")
        
        def on_suspended():
            logger.warning("Ably connection suspended")
        
        def on_closing():
            logger.info("Ably connection closing")
        
        def on_closed():
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
            "rebalancer_healthy": False
        }
        
        try:
            status["rebalancer_healthy"] = await self.rebalancer_client.health_check()
        except:
            pass
        
        return status