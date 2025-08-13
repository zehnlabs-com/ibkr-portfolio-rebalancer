"""
Dashboard API handlers for portfolio monitoring
"""
import json
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException
from app.models.dashboard_models import AccountData, AccountSummary, DashboardOverview, Position


class DashboardHandlers:
    """Handlers for dashboard API endpoints"""
    
    def __init__(self, redis_repository):
        self.redis_repository = redis_repository
    
    async def get_dashboard_overview(self) -> DashboardOverview:
        """Get system-wide dashboard overview"""
        try:
            # Get all account data from Redis
            accounts_data = await self._get_all_accounts_data()
            
            if not accounts_data:
                return DashboardOverview(
                    total_accounts=0,
                    total_value=0.0,
                    total_pnl=0.0,
                    total_pnl_percent=0.0,
                    accounts=[],
                    last_update=datetime.now()
                )
            
            # Calculate totals
            total_value = sum(acc.current_value for acc in accounts_data)
            total_pnl = sum(acc.todays_pnl for acc in accounts_data)
            total_pnl_percent = (total_pnl / (total_value - total_pnl)) * 100 if (total_value - total_pnl) != 0 else 0
            
            # Convert to summaries
            account_summaries = [
                AccountSummary(
                    account_id=acc.account_id,
                    strategy_name=acc.strategy_name,
                    current_value=acc.current_value,
                    todays_pnl=acc.todays_pnl,
                    todays_pnl_percent=acc.todays_pnl_percent,
                    positions_count=acc.positions_count,
                    last_update=acc.last_update
                ) for acc in accounts_data
            ]
            
            return DashboardOverview(
                total_accounts=len(accounts_data),
                total_value=total_value,
                total_pnl=total_pnl,
                total_pnl_percent=total_pnl_percent,
                accounts=account_summaries,
                last_update=max(acc.last_update for acc in accounts_data) if accounts_data else datetime.now()
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get dashboard overview: {str(e)}")
    
    async def get_accounts_summary(self) -> List[AccountSummary]:
        """Get summary data for all accounts"""
        try:
            accounts_data = await self._get_all_accounts_data()
            
            return [
                AccountSummary(
                    account_id=acc.account_id,
                    strategy_name=acc.strategy_name,
                    current_value=acc.current_value,
                    todays_pnl=acc.todays_pnl,
                    todays_pnl_percent=acc.todays_pnl_percent,
                    positions_count=acc.positions_count,
                    last_update=acc.last_update
                ) for acc in accounts_data
            ]
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get accounts summary: {str(e)}")
    
    async def get_account_details(self, account_id: str) -> AccountData:
        """Get detailed data for a specific account"""
        try:
            redis = self.redis_repository.redis
            if not redis:
                raise RuntimeError("Redis connection not established")
            account_data_str = await redis.get(f"account_data:{account_id}")
            
            if not account_data_str:
                raise HTTPException(status_code=404, detail=f"Account data not found for {account_id}")
            
            account_data_dict = json.loads(account_data_str)
            return self._parse_account_data(account_data_dict)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get account details: {str(e)}")
    
    async def get_account_positions(self, account_id: str) -> List[Position]:
        """Get positions for a specific account"""
        try:
            account_data = await self.get_account_details(account_id)
            return account_data.positions
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get account positions: {str(e)}")
    
    async def get_account_pnl(self, account_id: str) -> dict:
        """Get P&L data for a specific account"""
        try:
            account_data = await self.get_account_details(account_id)
            
            return {
                "account_id": account_data.account_id,
                "todays_pnl": account_data.todays_pnl,
                "todays_pnl_percent": account_data.todays_pnl_percent,
                "current_value": account_data.current_value,
                "last_close_netliq": account_data.last_close_netliq,
                "last_update": account_data.last_update
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get account P&L: {str(e)}")
    
    async def _get_all_accounts_data(self) -> List[AccountData]:
        """Helper method to get all account data from Redis"""
        try:
            redis = self.redis_repository.redis
            if not redis:
                raise RuntimeError("Redis connection not established")
            
            # Get all account_data:* keys
            keys = await redis.keys("account_data:*")
            
            if not keys:
                return []
            
            # Get all account data at once
            account_data_strings = await redis.mget(keys)
            
            accounts_data = []
            for i, data_str in enumerate(account_data_strings):
                if data_str:
                    try:
                        account_data_dict = json.loads(data_str)
                        account_data = self._parse_account_data(account_data_dict)
                        accounts_data.append(account_data)
                    except Exception as e:
                        # Log error but continue with other accounts
                        account_id = keys[i].split(':')[1] if ':' in keys[i] else 'unknown'
                        print(f"Failed to parse account data for {account_id}: {e}")
            
            return accounts_data
            
        except Exception as e:
            raise Exception(f"Failed to get accounts data from Redis: {str(e)}")
    
    def _parse_account_data(self, data: dict) -> AccountData:
        """Parse account data dictionary into AccountData model"""
        positions = [
            Position(
                symbol=pos['symbol'],
                quantity=pos['quantity'],
                market_value=pos['market_value'],
                avg_cost=pos['avg_cost'],
                current_price=pos['current_price'],
                unrealized_pnl=pos['unrealized_pnl'],
                unrealized_pnl_percent=pos['unrealized_pnl_percent']
            ) for pos in data.get('positions', [])
        ]
        
        # Parse last_rebalanced_on if present
        last_rebalanced_on = None
        if data.get('last_rebalanced_on'):
            try:
                last_rebalanced_on = datetime.fromisoformat(data['last_rebalanced_on'])
            except Exception:
                pass  # Ignore parse errors
        
        return AccountData(
            account_id=data['account_id'],
            strategy_name=data.get('strategy_name'),
            current_value=data['current_value'],
            last_close_netliq=data['last_close_netliq'],
            todays_pnl=data['todays_pnl'],
            todays_pnl_percent=data['todays_pnl_percent'],
            total_unrealized_pnl=data.get('total_unrealized_pnl', 0.0),
            positions=positions,
            positions_count=data['positions_count'],
            last_update=datetime.fromisoformat(data['last_update']),
            last_rebalanced_on=last_rebalanced_on
        )