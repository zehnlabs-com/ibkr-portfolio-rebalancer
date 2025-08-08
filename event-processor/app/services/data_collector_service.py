"""
Portfolio Data Collector Service for Dashboard

This service periodically collects portfolio data from IBKR for all accounts
and caches the data in Redis for dashboard consumption.
"""
import asyncio
import json
import os
import yaml
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.config import config
from app.logger import AppLogger
from app.services.ibkr_client import IBKRClient

app_logger = AppLogger(__name__)


class DataCollectorService:
    """Service for collecting and caching portfolio data for dashboard"""
    
    def __init__(self, ibkr_client: IBKRClient, redis_client):
        self.ibkr_client = ibkr_client
        self.redis_client = redis_client
        self._collection_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def start_collection_tasks(self) -> None:
        """Start background data collection tasks"""
        if self._running:
            app_logger.log_warning("Data collection already running")
            return
            
        self._running = True
        app_logger.log_info("Starting portfolio data collection service")
        
        # Start the main collection loop - let ib_async handle the complexity
        self._collection_task = asyncio.create_task(self._collection_loop())
        
    async def stop_collection_tasks(self) -> None:
        """Stop background data collection tasks"""
        self._running = False
        
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
                
        app_logger.log_info("Portfolio data collection service stopped")
        
    async def _collection_loop(self) -> None:
        """Main collection loop that runs every collection_interval seconds"""
        while self._running:
            try:
                await self.collect_all_accounts()
                await self.redis_client.set("collection:last_run", datetime.now(timezone.utc).isoformat())
                await self.redis_client.set("collection:status", "running")
                
            except Exception as e:
                app_logger.log_error(f"Error in data collection loop: {e}")
                await self.redis_client.set("collection:status", f"error: {str(e)}")
                
            # Wait for next collection interval
            collection_interval = getattr(config, 'data_collection', {}).get('collection_interval', 300)
            await asyncio.sleep(collection_interval)
            
    async def collect_all_accounts(self) -> None:
        """Collect portfolio data for all accounts in accounts.yaml"""
        accounts = self.load_accounts_config()
        if not accounts:
            app_logger.log_warning("No accounts found in accounts.yaml")
            return
            
        app_logger.log_info(f"Collecting data for {len(accounts)} accounts")
        
        # Process accounts sequentially to avoid overwhelming IBKR
        for account_id in accounts:
            try:
                await self.collect_account_data(account_id)
                await asyncio.sleep(1)  # Small delay between accounts
            except Exception as e:
                app_logger.log_error(f"Failed to collect data for account {account_id}: {e}")
                
    async def collect_account_data(self, account_id: str) -> None:
        """Collect and cache data for a single account"""
        try:
            app_logger.log_debug(f"Collecting data for account {account_id}")
            
            # Use existing IBKR client methods - let ib_async handle the complexity
            positions = await self.ibkr_client.get_positions(account_id)
            net_liq = await self.ibkr_client.get_account_value(account_id, "NetLiquidation")
            
            # Get P&L data directly from IBKR
            pnl_data = await self.ibkr_client.get_account_pnl(account_id)
            todays_pnl = pnl_data["daily_pnl"]
            
            # Calculate today's P&L percentage
            # If we have today's P&L, we can calculate the starting value
            # Starting value = Current value - Today's P&L
            if net_liq > 0 and todays_pnl != 0:
                starting_value = net_liq - todays_pnl
                if starting_value > 0:
                    todays_pnl_percent = (todays_pnl / starting_value) * 100
                else:
                    todays_pnl_percent = 0
            else:
                todays_pnl_percent = 0
            
            # For dashboard display, we still need a "last close" value
            # This would be today's net_liq minus today's P&L
            last_close_netliq = net_liq - todays_pnl if todays_pnl else net_liq
                
            # Enhanced position data
            enhanced_positions = []
            for position in positions:
                unrealized_pnl = position['market_value'] - (position['position'] * position['avg_cost'])
                unrealized_pnl_percent = (unrealized_pnl / (position['position'] * position['avg_cost'])) * 100 if position['position'] * position['avg_cost'] != 0 else 0
                current_price = position['market_value'] / position['position'] if position['position'] != 0 else 0
                
                enhanced_positions.append({
                    'symbol': position['symbol'],
                    'quantity': position['position'],
                    'market_value': position['market_value'],
                    'avg_cost': position['avg_cost'],
                    'current_price': current_price,
                    'unrealized_pnl': unrealized_pnl,
                    'unrealized_pnl_percent': unrealized_pnl_percent
                })
                
            # Build complete account data JSON document
            account_data = {
                "account_id": account_id,
                "current_value": net_liq,
                "last_close_netliq": last_close_netliq,
                "todays_pnl": todays_pnl,
                "todays_pnl_percent": todays_pnl_percent,
                "positions": enhanced_positions,
                "positions_count": len(enhanced_positions),
                "last_update": datetime.now(timezone.utc).isoformat()
            }
            
            # Simple Redis storage (no TTL - keep data available even during collection delays)
            await self.redis_client.set(
                f"account_data:{account_id}",
                json.dumps(account_data)
            )
            
            app_logger.log_debug(f"Cached data for account {account_id} with {len(enhanced_positions)} positions")
            
        except Exception as e:
            app_logger.log_error(f"Failed to collect account data for {account_id}: {e}")
            raise
            
    def load_accounts_config(self) -> List[str]:
        """Load account IDs from accounts.yaml filtered by TRADING_MODE"""
        try:
            accounts_path = os.path.join("/app", "accounts.yaml")
            if not os.path.exists(accounts_path):
                app_logger.log_warning(f"accounts.yaml not found at {accounts_path}")
                return []
                
            with open(accounts_path, 'r') as f:
                yaml_data = yaml.safe_load(f)
                
            if not yaml_data:
                return []
                
            # Get trading mode from config (defaults to 'paper')
            trading_mode = os.getenv('TRADING_MODE', 'paper').lower()
            
            # Extract account IDs from accounts array, filtered by type
            accounts_data = yaml_data.get('accounts', [])
            account_ids = [
                account.get('account_id') 
                for account in accounts_data 
                if account.get('account_id') and account.get('type', 'paper').lower() == trading_mode
            ]
                    
            app_logger.log_info(f"Loaded {len(account_ids)} {trading_mode} accounts from accounts.yaml")
            return account_ids
            
        except Exception as e:
            app_logger.log_error(f"Failed to load accounts config: {e}")
            return []