"""
Portfolio Data Collection Service for Dashboard

This service polls IBKR account data and caches it in Redis
for dashboard consumption with real-time WebSocket updates.
"""
import asyncio
import json
import math
import os
import yaml
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.config import config
from app.logger import AppLogger
from app.services.ibkr_client import IBKRClient

app_logger = AppLogger(__name__)


class DataCollectorService:
    """Service for periodic portfolio data collection and caching for dashboard"""
    
    def __init__(self, ibkr_client: IBKRClient, redis_client):
        self.ibkr_client = ibkr_client
        self.redis_client = redis_client
        self._collection_task: Optional[asyncio.Task] = None
        self._running = False
        self._accounts = []
        self._collection_interval = 60  # Poll every 60 seconds
        
    async def start_collection_tasks(self) -> None:
        """Start periodic data collection"""
        if self._running:
            app_logger.log_warning("Data collection already running")
            return
        
        self._running = True
        app_logger.log_info("Starting portfolio data collection service")
        
        # Load accounts from config
        self._accounts = self.load_accounts_config()
        if not self._accounts:
            app_logger.log_warning("No accounts found in accounts.yaml")
            return
        
        # Perform initial data sync to populate Redis
        await self.perform_initial_sync()
        
        # Start periodic collection task
        self._collection_task = asyncio.create_task(self._periodic_collection_loop())
        
        app_logger.log_info(f"Data collection service started for {len(self._accounts)} accounts (polling every {self._collection_interval}s)")
        
    async def stop_collection_tasks(self) -> None:
        """Stop periodic data collection"""
        self._running = False
        
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
                
        app_logger.log_info("Portfolio data collection service stopped")
    
    async def perform_initial_sync(self) -> None:
        """Perform initial data sync to populate Redis with current account data"""
        app_logger.log_debug(f"Performing initial sync for {len(self._accounts)} accounts")
        
        for account_id in self._accounts:
            try:
                await self.collect_account_data(account_id)
                await asyncio.sleep(1)  # Small delay to avoid overwhelming IBKR
            except Exception as e:
                app_logger.log_error(f"Failed to sync initial data for account {account_id}: {e}")
                continue
        
        # Publish initial dashboard summary
        await self._publish_dashboard_summary_update()
        await self.redis_client.set("collection:last_run", datetime.now(timezone.utc).isoformat())
        await self.redis_client.set("collection:status", "polling")
        
        app_logger.log_info("Initial data sync completed")
    
    async def _periodic_collection_loop(self) -> None:
        """Main loop for periodic data collection"""
        while self._running:
            try:
                # Wait for the next collection interval
                await asyncio.sleep(self._collection_interval)
                
                if not self._running:
                    break
                
                app_logger.log_debug(f"Starting periodic data collection for {len(self._accounts)} accounts")
                
                # Collect data for all accounts
                for account_id in self._accounts:
                    if not self._running:
                        break
                    
                    try:
                        await self.collect_account_data(account_id)
                        await asyncio.sleep(1)  # Small delay between accounts
                    except Exception as e:
                        app_logger.log_error(f"Failed to collect data for account {account_id}: {e}")
                        continue
                
                # Update dashboard summary
                await self._publish_dashboard_summary_update()
                await self.redis_client.set("collection:last_run", datetime.now(timezone.utc).isoformat())
                
                app_logger.log_debug("Periodic data collection completed")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                app_logger.log_error(f"Error in periodic collection loop: {e}")
                await asyncio.sleep(10)  # Brief pause before retrying
                
    async def collect_account_data(self, account_id: str) -> None:
        """Collect and cache data for a single account"""
        try:
            app_logger.log_debug(f"Collecting data for account {account_id}")
            
            # Use portfolio() method to get complete position data with market prices
            portfolio_items = await self.ibkr_client.get_portfolio_items(account_id)
            net_liq = await self.ibkr_client.get_account_value(account_id, "NetLiquidation")
            
            # Get P&L data directly from IBKR
            pnl_data = await self.ibkr_client.get_account_pnl(account_id)
            todays_pnl = pnl_data["daily_pnl"]
            total_upnl = pnl_data["unrealized_pnl"]
            
            # Get IRA status from accounts.yaml (based on replacement_set)
            account_config = self._accounts.get(account_id, {})
            is_ira = account_config.get("replacement_set") == "ira"
            
            # Get cash balance
            cash_balance = await self.ibkr_client.get_account_value(account_id, "TotalCashBalance")
            
            # Prepare dashboard data
            account_data = {
                "account_id": account_id,
                "account_name": account_config.get("name", account_id),
                "strategy_name": account_config.get("strategy"),
                "is_ira": is_ira,
                "net_liquidation": net_liq,
                "cash_balance": cash_balance,
                "todays_pnl": todays_pnl,
                "todays_pnl_percent": (todays_pnl / (net_liq - todays_pnl) * 100) if net_liq > todays_pnl else 0,
                "total_upnl": total_upnl,
                "total_upnl_percent": (total_upnl / net_liq * 100) if net_liq > 0 else 0,
                "positions": []
            }
            
            # Calculate invested amount and process positions
            invested_amount = 0.0
            
            if portfolio_items:
                for item in portfolio_items:
                    symbol = item['symbol']
                    position = item['position']
                    market_price = item['market_price']
                    market_value = item['market_value']
                    avg_cost = item['avg_cost']
                    
                    if position != 0:
                        cost_basis = avg_cost * abs(position)
                        unrealized_pnl = item['unrealized_pnl']
                        unrealized_pnl_percent = (unrealized_pnl / cost_basis * 100) if cost_basis != 0 else 0
                        
                        position_data = {
                            "symbol": symbol,
                            "position": position,
                            "market_price": market_price,
                            "market_value": market_value,
                            "avg_cost": avg_cost,
                            "cost_basis": cost_basis,
                            "unrealized_pnl": unrealized_pnl,
                            "unrealized_pnl_percent": unrealized_pnl_percent,
                            "weight": (market_value / net_liq * 100) if net_liq > 0 else 0
                        }
                        
                        account_data["positions"].append(position_data)
                        invested_amount += market_value
            
            # Update invested amount
            account_data["invested_amount"] = invested_amount
            account_data["cash_percent"] = ((net_liq - invested_amount) / net_liq * 100) if net_liq > 0 else 0
            account_data["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            # Save to Redis
            await self.redis_client.set(f"account:{account_id}", json.dumps(account_data))
            
            # Publish update notification
            await self._publish_account_update(account_id)
            
            app_logger.log_debug(f"Successfully collected data for account {account_id}")
            
        except Exception as e:
            app_logger.log_error(f"Failed to collect account data for {account_id}: {e}")
            raise
            
    async def _publish_account_update(self, account_id: str) -> None:
        """Publish account update notification via Redis pub/sub"""
        try:
            message = {
                "type": "account_data_updated",
                "account_id": account_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await self.redis_client.publish("dashboard_updates", json.dumps(message))
            app_logger.log_debug(f"Published account update notification for {account_id}")
        except Exception as e:
            app_logger.log_error(f"Failed to publish account update: {e}")
            
    async def _publish_dashboard_summary_update(self) -> None:
        """Publish dashboard summary update notification"""
        try:
            # Calculate summary statistics
            total_value = 0
            total_pnl_today = 0
            total_accounts = 0
            
            for account_id in self._accounts:
                account_data = await self.redis_client.get(f"account:{account_id}")
                if account_data:
                    data = json.loads(account_data)
                    total_value += data.get("net_liquidation", 0)
                    total_pnl_today += data.get("todays_pnl", 0)
                    total_accounts += 1
            
            summary = {
                "total_value": total_value,
                "total_pnl_today": total_pnl_today,
                "total_pnl_today_percent": (total_pnl_today / (total_value - total_pnl_today) * 100) if total_value > total_pnl_today else 0,
                "total_accounts": total_accounts,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            await self.redis_client.set("dashboard:summary", json.dumps(summary))
            
            # Publish notification
            message = {
                "type": "dashboard_summary_updated",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await self.redis_client.publish("dashboard_updates", json.dumps(message))
            app_logger.log_debug("Published dashboard summary update notification")
            
        except Exception as e:
            app_logger.log_error(f"Failed to publish dashboard summary: {e}")
    
    def load_accounts_config(self) -> dict:
        """Load accounts configuration from accounts.yaml"""
        try:
            accounts_file = "accounts.yaml"
            with open(accounts_file, 'r') as f:
                config_data = yaml.safe_load(f)
                
            accounts = {}
            for account in config_data.get('accounts', []):
                if account.get('type') == 'live' and account.get('enabled', False):
                    account_id = account.get('account_id')
                    if account_id:
                        accounts[account_id] = {
                            'name': account.get('name', account_id),
                            'replacement_set': account.get('replacement_set'),
                            'strategy': account.get('strategy_name')
                        }
            
            app_logger.log_info(f"Loaded {len(accounts)} live accounts from accounts.yaml")
            return accounts
            
        except Exception as e:
            app_logger.log_error(f"Failed to load accounts configuration: {e}")
            return {}