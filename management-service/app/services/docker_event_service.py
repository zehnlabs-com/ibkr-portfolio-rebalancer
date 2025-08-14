"""
Docker Real-Time Event Service

This service streams Docker events in real-time and broadcasts container 
status changes via WebSocket for immediate dashboard updates.
"""
import asyncio
import json
import threading
from datetime import datetime
from typing import Optional, Dict, Any
import docker
from docker.errors import DockerException
from app.logger import setup_logger

logger = setup_logger(__name__)


class DockerEventService:
    """Service for streaming Docker events in real-time"""
    
    def __init__(self, websocket_manager, docker_handlers):
        self.websocket_manager = websocket_manager
        self.docker_handlers = docker_handlers
        self.docker_client = None
        self._event_stream = None
        self._event_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Initialize Docker client
        self._initialize_docker_client()
    
    def _initialize_docker_client(self):
        """Initialize Docker client with error handling"""
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("Docker event service: Client connected successfully")
        except DockerException as e:
            logger.warning(f"Docker event service: Failed to connect to Docker: {e}")
            self.docker_client = None
    
    async def start_event_stream(self) -> None:
        """Start listening to Docker event stream"""
        if self._running:
            logger.warning("Docker event stream already running")
            return
        
        if not self.docker_client:
            logger.warning("Docker client not available, skipping event stream")
            return
        
        self._running = True
        logger.info("Starting Docker event stream")
        
        # Start the event streaming task
        self._event_task = asyncio.create_task(self._event_stream_loop())
        
        logger.info("Docker event stream started successfully")
    
    async def stop_event_stream(self) -> None:
        """Stop Docker event stream and cleanup"""
        self._running = False
        
        if self._event_task:
            self._event_task.cancel()
            try:
                await self._event_task
            except asyncio.CancelledError:
                pass
        
        if self._event_stream:
            try:
                self._event_stream.close()
            except Exception as e:
                logger.warning(f"Error closing event stream: {e}")
        
        logger.info("Docker event stream stopped")
    
    async def _event_stream_loop(self) -> None:
        """Main event stream loop running in executor"""
        try:
            # Run the blocking event stream in a thread executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._stream_docker_events, loop)
        except Exception as e:
            logger.error(f"Error in Docker event stream loop: {e}")
    
    def _stream_docker_events(self, event_loop) -> None:
        """Stream Docker events (runs in thread executor)"""
        try:
            # Create event stream with filters for container events
            filters = {'type': 'container'}
            self._event_stream = self.docker_client.events(decode=True, filters=filters)
            
            logger.info("Docker event stream connected")
            
            for event in self._event_stream:
                if not self._running:
                    break
                
                try:
                    # Schedule the async event handler with the passed event loop
                    asyncio.run_coroutine_threadsafe(
                        self._handle_container_event(event),
                        event_loop
                    )
                except Exception as e:
                    logger.error(f"Error scheduling event handler: {e}")
                    
        except Exception as e:
            logger.error(f"Error in Docker event stream: {e}")
        finally:
            logger.info("Docker event stream disconnected")
    
    async def _handle_container_event(self, event: Dict[str, Any]) -> None:
        """Handle individual container events"""
        try:
            action = event.get('Action', '')
            container_id = event.get('Actor', {}).get('ID', '')
            container_name = event.get('Actor', {}).get('Attributes', {}).get('name', 'unknown')
            
            # Only handle relevant lifecycle events
            relevant_actions = ['start', 'stop', 'restart', 'die', 'health_status', 'kill', 'pause', 'unpause']
            
            if action in relevant_actions and container_id:
                logger.info(f"Container event: {action} for {container_name} ({container_id[:12]})")
                
                # Get fresh container data
                container_data = await self._get_container_data(container_id)
                
                if container_data:
                    # Broadcast container update via WebSocket
                    await self._broadcast_container_update(container_data)
                else:
                    logger.warning(f"Could not get data for container {container_id[:12]}")
            
        except Exception as e:
            logger.error(f"Error handling container event: {e}")
    
    async def _get_container_data(self, container_id: str) -> Optional[Dict[str, Any]]:
        """Get fresh container data after an event"""
        try:
            if not self.docker_client:
                return None
            
            # Get container by ID
            container = self.docker_client.containers.get(container_id)
            
            # Get container stats if running
            stats = None
            if container.status == 'running':
                try:
                    stats_data = container.stats(stream=False)
                    stats = self.docker_handlers._parse_container_stats(stats_data)
                except Exception as e:
                    logger.debug(f"Failed to get stats for {container.name}: {e}")
            
            # Get image name safely
            image_name = 'unknown'
            try:
                if container.image and hasattr(container.image, 'tags') and container.image.tags:
                    image_name = container.image.tags[0]
                elif container.image and hasattr(container.image, 'id'):
                    image_name = container.image.id[:12]
            except Exception:
                image_name = container.attrs.get('Config', {}).get('Image', 'unknown')
            
            container_data = {
                'id': container.id[:12],
                'name': container.name,
                'image': image_name,
                'status': container.status,
                'state': container.attrs.get('State', {}).get('Status', 'unknown'),
                'created': container.attrs.get('Created', ''),
                'ports': self.docker_handlers._format_ports(container.ports),
                'stats': stats,
                'last_update': datetime.now().isoformat()
            }
            
            return container_data
            
        except docker.errors.NotFound:
            logger.debug(f"Container {container_id[:12]} not found (may have been removed)")
            return None
        except Exception as e:
            logger.error(f"Error getting container data for {container_id[:12]}: {e}")
            return None
    
    async def _broadcast_container_update(self, container_data: Dict[str, Any]) -> None:
        """Broadcast container update via WebSocket"""
        try:
            # Send container update to all connected WebSocket clients
            message = {
                "type": "container_event",
                "data": container_data,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.websocket_manager.broadcast(message)
            
            logger.info(f"Broadcast container update for {container_data['name']} (status: {container_data['status']})")
            
        except Exception as e:
            logger.error(f"Error broadcasting container update: {e}")