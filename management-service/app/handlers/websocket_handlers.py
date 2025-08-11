"""
WebSocket handlers for real-time dashboard updates
"""
import json
import asyncio
import logging
from typing import Dict, Set, Any
from fastapi import WebSocket, WebSocketDisconnect
from app.logger import setup_logger

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
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients"""
        if not self.active_connections:
            return
            
        disconnected = set()
        message_str = json.dumps(message)
        
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
    
    def __init__(self):
        self.manager = websocket_manager
    
    async def dashboard_stream(self, websocket: WebSocket):
        """Handle WebSocket connection for dashboard real-time updates"""
        await self.manager.connect(websocket)
        try:
            # Send initial connection success message
            await websocket.send_text(json.dumps({
                "type": "connection_established",
                "message": "Real-time dashboard stream connected"
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
                                    await websocket.send_text(json.dumps({"type": "pong"}))
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