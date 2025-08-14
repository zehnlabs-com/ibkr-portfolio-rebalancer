"""
WebSocket handlers for real-time dashboard updates
"""
import json
import asyncio
import logging
import math
from typing import Dict, Set, Any
from fastapi import WebSocket, WebSocketDisconnect
from app.logger import setup_logger

class SafeJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles NaN and infinity values"""
    
    def _sanitize_value(self, obj):
        """Recursively sanitize NaN and infinity values in nested structures"""
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return 0
            return obj
        elif isinstance(obj, dict):
            return {k: self._sanitize_value(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize_value(v) for v in obj]
        elif isinstance(obj, tuple):
            return tuple(self._sanitize_value(v) for v in obj)
        return obj
    
    def encode(self, obj):
        """Encode after sanitizing the object"""
        sanitized = self._sanitize_value(obj)
        return super().encode(sanitized)
    
    def iterencode(self, obj, _one_shot=False):
        """Encode the given object and return an iterator of string chunks."""
        sanitized = self._sanitize_value(obj)
        return super().iterencode(sanitized, _one_shot)

def safe_json_dumps(obj):
    """JSON dumps with NaN/infinity handling"""
    return json.dumps(obj, cls=SafeJSONEncoder)

logger = setup_logger(__name__)

class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Store active connections
        self.active_connections: Set[WebSocket] = set()
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        try:
            await websocket.accept()
            self.active_connections.add(websocket)
            self.connection_info[websocket] = {
                "connected_at": asyncio.get_event_loop().time(),
                "client_info": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
            }
            logger.info(f"WebSocket connected: {self.connection_info[websocket]['client_info']}")
            logger.info(f"Total connections: {len(self.active_connections)}")
        except Exception as e:
            logger.error(f"Error accepting WebSocket connection: {e}")
            raise
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            client_info = self.connection_info.get(websocket, {}).get("client_info", "unknown")
            if websocket in self.connection_info:
                del self.connection_info[websocket]
            logger.info(f"WebSocket disconnected: {client_info}")
            logger.info(f"Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific connection"""
        try:
            await websocket.send_text(safe_json_dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients"""
        if not self.active_connections:
            return
            
        disconnected = set()
        message_str = safe_json_dumps(message)
        
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_account_update(self, account_data: Dict[str, Any]):
        """Send account update to all connected clients"""
        message = {
            "type": "account_update",
            "data": account_data
        }
        await self.broadcast(message)
    
    async def send_container_status(self, container_data: Dict[str, Any]):
        """Send container status update to all connected clients"""
        message = {
            "type": "container_status", 
            "data": container_data
        }
        await self.broadcast(message)
    
    async def send_system_status(self, system_data: Dict[str, Any]):
        """Send system status update to all connected clients"""
        message = {
            "type": "system_status",
            "data": system_data
        }
        await self.broadcast(message)
    
    async def send_notification_count_update(self, unread_count: int):
        """Send notification count update to all connected clients"""
        message = {
            "type": "notification_count_update",
            "data": {"unread_count": unread_count}
        }
        await self.broadcast(message)

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

class WebSocketHandlers:
    """WebSocket endpoint handlers"""
    
    def __init__(self, dashboard_handlers=None):
        self.manager = websocket_manager
        self.dashboard_handlers = dashboard_handlers
    
    async def _send_container_data_async(self, websocket: WebSocket):
        """Send container data asynchronously to avoid blocking other data"""
        try:
            from app.container import container
            containers_data = await container.docker_handlers.get_containers()
            
            container_message = {
                "type": "container",
                "action": "update", 
                "data": containers_data,
                "timestamp": safe_json_dumps({"timestamp": "now"})
            }
            await websocket.send_text(safe_json_dumps(container_message))
            logger.info(f"Sent initial container data with {len(containers_data)} containers")
        except Exception as e:
            logger.error(f"Error sending container data: {e}")
    
    async def dashboard_stream(self, websocket: WebSocket):
        """Handle WebSocket connection for dashboard real-time updates"""
        await self.manager.connect(websocket)
        try:
            # Send initial connection success message
            await websocket.send_text(safe_json_dumps({
                "type": "connection_established",
                "message": "Real-time dashboard stream connected"
            }))
            
            # Send initial dashboard data if dashboard_handlers is available
            if self.dashboard_handlers:
                try:
                    accounts_data = await self.dashboard_handlers._get_all_accounts_data()
                    
                    # Calculate dashboard summary data with safe math
                    total_value = sum(account.current_value for account in accounts_data)
                    total_pnl = sum(account.todays_pnl for account in accounts_data)
                    
                    # Safe percentage calculation to avoid division by zero
                    denominator = total_value - total_pnl
                    if denominator > 0:
                        total_pnl_percent = (total_pnl / denominator) * 100
                    else:
                        total_pnl_percent = 0.0
                    
                    total_positions = sum(account.positions_count for account in accounts_data)
                    
                    dashboard_data = {
                        "type": "dashboard",
                        "action": "update",
                        "data": {
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
                        },
                        "timestamp": safe_json_dumps({"timestamp": "now"})
                    }
                    
                    await websocket.send_text(safe_json_dumps(dashboard_data))
                    logger.info(f"Sent initial dashboard data with {len(accounts_data)} accounts")
                    
                    # Also send account data for AccountList component
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
                        ],
                        "timestamp": safe_json_dumps({"timestamp": "now"})
                    }
                    await websocket.send_text(safe_json_dumps(account_message))
                    logger.info(f"Sent initial account data with {len(accounts_data)} accounts")
                    
                    # Send individual account details for each account so AccountShow pages work immediately
                    for account in accounts_data:
                        account_detail_message = {
                            "type": "account_update",
                            "data": {
                                "account_id": account.account_id,
                                "strategy_name": account.strategy_name,
                                "current_value": account.current_value,
                                "last_close_netliq": account.last_close_netliq,
                                "todays_pnl": account.todays_pnl,
                                "todays_pnl_percent": account.todays_pnl_percent,
                                "total_unrealized_pnl": account.total_unrealized_pnl,
                                "positions": [
                                    {
                                        "symbol": pos.symbol,
                                        "quantity": pos.quantity,
                                        "market_value": pos.market_value,
                                        "avg_cost": pos.avg_cost,
                                        "current_price": pos.current_price,
                                        "unrealized_pnl": pos.unrealized_pnl,
                                        "unrealized_pnl_percent": pos.unrealized_pnl_percent
                                    } for pos in account.positions
                                ],
                                "positions_count": account.positions_count,
                                "last_update": account.last_update.isoformat(),
                                "last_rebalanced_on": account.last_rebalanced_on.isoformat() if account.last_rebalanced_on else None
                            }
                        }
                        await websocket.send_text(safe_json_dumps(account_detail_message))
                    
                    logger.info(f"Sent initial account details for {len(accounts_data)} accounts")
                    
                    # Send container data asynchronously to avoid blocking dashboard/account data
                    asyncio.create_task(self._send_container_data_async(websocket))
                except Exception as e:
                    logger.error(f"Error sending initial dashboard data: {e}")
                    # Send a basic message so frontend doesn't timeout
                    await websocket.send_text(safe_json_dumps({
                        "type": "dashboard",
                        "action": "update", 
                        "data": {
                            "total_value": 0,
                            "total_pnl": 0,
                            "total_pnl_percent": 0,
                            "total_positions": 0,
                            "accounts_count": 0,
                            "accounts": [],
                            "last_update": None
                        },
                        "timestamp": safe_json_dumps({"timestamp": "now"})
                    }))
            
            while True:
                # Keep the connection alive and listen for client messages
                # Client can send ping/pong or subscription preferences
                try:
                    # Use receive() instead of receive_text() to handle different message types
                    message = await websocket.receive()
                    
                    if message["type"] == "websocket.receive":
                        # Handle text messages
                        if "text" in message:
                            try:
                                data = json.loads(message["text"])
                                if data.get("type") == "ping":
                                    await websocket.send_text(safe_json_dumps({"type": "pong"}))
                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON received: {message['text']}")
                    elif message["type"] == "websocket.disconnect":
                        logger.info("WebSocket disconnect message received")
                        break
                        
                except Exception as e:
                    logger.error(f"Error receiving WebSocket message: {e}")
                    break
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected normally")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.manager.disconnect(websocket)

def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance"""
    return websocket_manager