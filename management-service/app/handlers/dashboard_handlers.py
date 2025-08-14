"""
Dashboard API handlers for portfolio monitoring
"""
import json
from datetime import datetime
from typing import List, Optional
from app.models.dashboard_models import AccountData, Position


class DashboardHandlers:
    """Handlers for dashboard API endpoints"""
    
    def __init__(self, redis_repository):
        self.redis_repository = redis_repository
    
    async def _get_all_accounts_data(self) -> List[AccountData]:
        """Helper method to get all account data from Redis"""
        try:
            redis = self.redis_repository.redis
            if not redis:
                raise RuntimeError("Redis connection not established")
            
            # Get all account:* keys
            keys = await redis.keys("account:*")
            
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
        # Bypass Position model validation and use raw dict data
        positions = []
        for pos in data.get('positions', []):
            try:
                position_data = Position(
                    symbol=pos['symbol'],
                    quantity=pos['position'],  # Redis stores as 'position'
                    market_value=pos['market_value'],
                    avg_cost=pos['avg_cost'],
                    current_price=pos['market_price'],  # Redis stores as 'market_price'
                    unrealized_pnl=pos['unrealized_pnl'],
                    unrealized_pnl_percent=pos['unrealized_pnl_percent']
                )
                positions.append(position_data)
            except Exception as e:
                # Log the error but continue with other positions
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to parse position {pos.get('symbol', 'unknown')}: {e}")
                continue
        
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
            current_value=data['net_liquidation'],  # Redis stores as 'net_liquidation'
            last_close_netliq=data.get('net_liquidation', 0) - data.get('todays_pnl', 0),  # Calculate from current - today's PnL
            todays_pnl=data['todays_pnl'],
            todays_pnl_percent=data['todays_pnl_percent'],
            total_unrealized_pnl=data.get('total_upnl', 0.0),  # Redis stores as 'total_upnl'
            positions=positions,
            positions_count=len(positions),  # Calculate from positions array
            last_update=datetime.fromisoformat(data['last_updated']),  # Redis stores as 'last_updated'
            last_rebalanced_on=last_rebalanced_on
        )