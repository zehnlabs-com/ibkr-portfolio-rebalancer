import unittest
from unittest.mock import Mock, AsyncMock
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.rebalancer_service import RebalancerService, RebalanceOrder

class TestRebalancerService(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.mock_ibkr_client = Mock()
        self.rebalancer = RebalancerService(self.mock_ibkr_client)
    
    async def test_calculate_rebalance_orders_buy_scenario(self):
        # Mock data
        target_allocations = [
            {"symbol": "SPY", "allocation": 0.6},
            {"symbol": "QQQ", "allocation": 0.4}
        ]
        
        current_positions = [
            {"symbol": "SPY", "position": 10, "market_value": 4000},
            {"symbol": "QQQ", "position": 5, "market_value": 1500}
        ]
        
        account_value = 10000
        
        # Mock market prices
        self.mock_ibkr_client.get_market_price = AsyncMock()
        self.mock_ibkr_client.get_market_price.side_effect = lambda symbol: {
            "SPY": 400.0,
            "QQQ": 300.0
        }[symbol]
        
        # Calculate orders
        orders = await self.rebalancer._calculate_rebalance_orders(
            target_allocations, current_positions, account_value
        )
        
        # Assertions
        self.assertEqual(len(orders), 2)
        
        # Check SPY order (should buy more)
        spy_order = next(order for order in orders if order.symbol == "SPY")
        self.assertEqual(spy_order.action, "BUY")
        self.assertGreater(spy_order.quantity, 0)
        
        # Check QQQ order (should buy more)
        qqq_order = next(order for order in orders if order.symbol == "QQQ")
        self.assertEqual(qqq_order.action, "BUY")
        self.assertGreater(qqq_order.quantity, 0)
    
    async def test_calculate_rebalance_orders_sell_scenario(self):
        # Mock data - overweight positions
        target_allocations = [
            {"symbol": "SPY", "allocation": 0.3},
            {"symbol": "QQQ", "allocation": 0.2}
        ]
        
        current_positions = [
            {"symbol": "SPY", "position": 20, "market_value": 8000},
            {"symbol": "QQQ", "position": 10, "market_value": 3000},
            {"symbol": "TSLA", "position": 5, "market_value": 1000}  # Not in target
        ]
        
        account_value = 12000
        
        # Mock market prices
        self.mock_ibkr_client.get_market_price = AsyncMock()
        self.mock_ibkr_client.get_market_price.side_effect = lambda symbol: {
            "SPY": 400.0,
            "QQQ": 300.0,
            "TSLA": 200.0
        }[symbol]
        
        # Calculate orders
        orders = await self.rebalancer._calculate_rebalance_orders(
            target_allocations, current_positions, account_value
        )
        
        # Should have orders to sell excess positions
        tsla_order = next(order for order in orders if order.symbol == "TSLA")
        self.assertEqual(tsla_order.action, "SELL")
        self.assertEqual(tsla_order.quantity, 5)  # Sell all TSLA
    
    def test_rebalance_order_creation(self):
        order = RebalanceOrder("SPY", 10, "BUY", 4000.0)
        
        self.assertEqual(order.symbol, "SPY")
        self.assertEqual(order.quantity, 10)
        self.assertEqual(order.action, "BUY")
        self.assertEqual(order.market_value, 4000.0)
        
        # Test string representation
        self.assertIn("BUY 10 shares of SPY", str(order))

if __name__ == '__main__':
    unittest.main()