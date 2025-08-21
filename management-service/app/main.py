"""
Management Service FastAPI Application - SOLID Principles Implementation
"""
import logging
import os
from typing import List, Dict, Any
from fastapi import FastAPI, Depends, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.container import container
from app.models.queue_models import QueueStatus, QueueEvent, AddEventRequest, AddEventResponse, RemoveEventResponse, ClearQueuesResponse
from app.models.health_models import DetailedHealthStatus
from app.handlers.auth_handlers import UserValidationRequest, UserValidationResponse
from app.config.settings import settings

# Configure logging
from app.logger import configure_root_logger, setup_logger
configure_root_logger(settings.log_level)
logger = setup_logger(__name__, settings.log_level)

# Get version from environment variable (set by Docker)
VERSION = os.getenv('SERVICE_VERSION', '1.0.0')

# Initialize FastAPI app
app = FastAPI(
    title="Portfolio Rebalancer Management Service",
    description="Queue management and health monitoring for the portfolio rebalancer system",
    version=VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Portfolio Rebalancer Management Service", "version": VERSION}

# Health endpoints (public)
@app.get("/health", response_model=DetailedHealthStatus)
async def health_check():
    """Health check endpoint"""
    return await container.health_handlers.detailed_health_check()

# Queue status endpoints (public)
@app.get("/queue/status", response_model=QueueStatus)
async def get_queue_status():
    """Get queue status"""
    return await container.queue_handlers.get_queue_status()

@app.get("/queue/events", response_model=List[QueueEvent])
async def get_queue_events(
    limit: int = Query(100, ge=1, le=1000),
    type: str = Query(None, regex="^(active|retry|delayed)$", description="Filter by event type: 'active', 'retry', or 'delayed'")
):
    """Get events from queue with optional type filtering"""
    return await container.queue_handlers.get_queue_events(limit=limit, event_type=type)

# Queue management endpoints
@app.delete("/queue/events/{event_id}", response_model=RemoveEventResponse)
async def remove_event(event_id: str):
    """Remove event from queue"""
    return await container.queue_handlers.remove_event(event_id)

@app.post("/queue/events", response_model=AddEventResponse)
async def add_event(event_request: AddEventRequest):
    """Add event to queue"""
    return await container.queue_handlers.add_event(event_request)

@app.delete("/queue/events", response_model=ClearQueuesResponse)  
async def clear_all_queues():
    """Clear all events from all queues"""
    return await container.queue_handlers.clear_all_queues()

# Authentication endpoints
@app.post("/api/auth/validate-user", response_model=UserValidationResponse)
async def validate_user(request: UserValidationRequest):
    """Validate user against clerk-users.json"""
    return await container.auth_handlers.validate_user(request)

# Account rebalance endpoint
@app.post("/api/accounts/{account_id}/rebalance")
async def trigger_account_rebalance(account_id: str):
    """Trigger rebalance for a specific account"""
    return await container.queue_handlers.trigger_account_rebalance(account_id)

# Notification endpoints
@app.get("/api/notifications")
async def get_notifications(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """Get paginated notifications"""
    return await container.notification_handlers.get_notifications(offset, limit)

@app.get("/api/notifications/unread-count")
async def get_unread_count():
    """Get count of unread notifications"""
    return await container.notification_handlers.get_unread_count()

@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark a specific notification as read"""
    return await container.notification_handlers.mark_notification_read(notification_id)

@app.put("/api/notifications/read-all")
async def mark_all_notifications_read():
    """Mark all notifications as read"""
    return await container.notification_handlers.mark_all_notifications_read()

@app.delete("/api/notifications/{notification_id}")
async def delete_notification(notification_id: str):
    """Delete a specific notification"""
    return await container.notification_handlers.delete_notification(notification_id)

@app.post("/api/containers/{container_name}/start")
async def start_container(container_name: str):
    """Start a container"""
    return await container.docker_handlers.start_container(container_name)

@app.post("/api/containers/{container_name}/stop")
async def stop_container(container_name: str):
    """Stop a container"""
    return await container.docker_handlers.stop_container(container_name)

@app.post("/api/containers/{container_name}/restart")
async def restart_container(container_name: str):
    """Restart a container"""
    return await container.docker_handlers.restart_container(container_name)

# Strategies endpoints
@app.get("/api/strategies")
async def get_strategies():
    """Get available strategies from Zehnlabs Workers API"""
    return await container.strategies_handlers.get_strategies()

# VNC configuration endpoint
@app.get("/api/config/vnc")
async def get_vnc_config():
    """Get VNC configuration for NoVNC client"""
    # Get env config from the mounted .env file
    env_data = await container.config_handlers.get_env_config()
    
    # Extract VNC configuration with defaults
    vnc_host = "ws://ibkr-portfolio-rebalancer-9897:5900"
    vnc_password = ""
    
    if env_data.get("file_exists") and env_data.get("config"):
        config = env_data["config"]
        vnc_host = config.get("VNC_HOST", vnc_host)
        vnc_password = config.get("VNC_PASSWORD", vnc_password)
    
    return {
        "host": vnc_host,
        "password": vnc_password
    }

# Configuration management endpoints
@app.get("/api/config/env")
async def get_env_config():
    """Get current .env configuration"""
    return await container.config_handlers.get_env_config()

@app.put("/api/config/env")
async def update_env_config(config: Dict[str, str]):
    """Update .env configuration"""
    return await container.config_handlers.update_env_config(config)

@app.get("/api/config/accounts")
async def get_accounts_config():
    """Get current accounts.yaml configuration"""
    return await container.config_handlers.get_accounts_config()

@app.put("/api/config/accounts")
async def update_accounts_config(config: Dict[str, Any]):
    """Update accounts.yaml configuration"""
    return await container.config_handlers.update_accounts_config(config)

@app.get("/api/config/replacement-sets")
async def get_replacement_sets_config():
    """Get current replacement-sets.yaml configuration"""
    return await container.config_handlers.get_replacement_sets_config()

@app.put("/api/config/replacement-sets")
async def update_replacement_sets_config(config: Dict[str, Any]):
    """Update replacement-sets.yaml configuration"""
    return await container.config_handlers.update_replacement_sets_config(config)

@app.post("/api/config/restart-services")
async def restart_affected_services(config_type: str = Query(..., regex="^(env|accounts|replacement-sets)$")):
    """Restart services affected by configuration changes"""
    return await container.config_handlers.restart_affected_services(config_type)

@app.get("/api/config/backups")
async def get_config_backups():
    """Get list of configuration file backups"""
    return await container.config_handlers.get_config_backups()

# WebSocket endpoint for real-time updates
@app.websocket("/api/dashboard/stream")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    await container.websocket_handlers.dashboard_stream(websocket)

# WebSocket endpoint for real-time container logs
@app.websocket("/api/containers/{container_name}/logs/stream")
async def container_logs_websocket(websocket: WebSocket, container_name: str):
    """WebSocket endpoint for real-time container log streaming"""
    logger.info(f"Container logs WebSocket endpoint hit for: {container_name}")
    try:
        logger.info(f"Attempting to accept WebSocket connection for container: {container_name}")
        await websocket.accept()
        logger.info(f"WebSocket accepted for container logs: {container_name}")
        await container.docker_handlers.stream_container_logs(container_name, websocket, tail=50)
    except Exception as e:
        logger.error(f"Error in container logs WebSocket: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            await websocket.close()
        except:
            pass

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    try:
        await container.startup()
        logger.info("Management service started successfully")
    except Exception as e:
        logger.error(f"Failed to start management service: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown"""
    try:
        await container.shutdown()
        logger.info("Management service shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False
    )