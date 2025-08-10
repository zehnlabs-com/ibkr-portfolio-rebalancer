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
from app.models.dashboard_models import DashboardOverview, AccountData, AccountSummary, Position
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

# Dashboard endpoints
@app.get("/api/dashboard/overview", response_model=DashboardOverview)
async def get_dashboard_overview():
    """Get system-wide portfolio overview"""
    return await container.dashboard_handlers.get_dashboard_overview()

@app.get("/api/dashboard/accounts", response_model=List[AccountSummary])
async def get_accounts_summary():
    """Get summary data for all accounts"""
    return await container.dashboard_handlers.get_accounts_summary()

@app.get("/api/dashboard/accounts/{account_id}", response_model=AccountData)
async def get_account_details(account_id: str):
    """Get detailed data for a specific account"""
    return await container.dashboard_handlers.get_account_details(account_id)

@app.get("/api/dashboard/accounts/{account_id}/positions", response_model=List[Position])
async def get_account_positions(account_id: str):
    """Get positions for a specific account"""
    return await container.dashboard_handlers.get_account_positions(account_id)

@app.get("/api/dashboard/accounts/{account_id}/pnl")
async def get_account_pnl(account_id: str):
    """Get P&L data for a specific account"""
    return await container.dashboard_handlers.get_account_pnl(account_id)

# Docker management endpoints
@app.get("/api/containers")
async def get_containers():
    """Get list of all containers with status and stats"""
    return await container.docker_handlers.get_containers()

@app.get("/api/containers/{container_name}/stats")
async def get_container_stats(container_name: str):
    """Get detailed stats for a specific container"""
    return await container.docker_handlers.get_container_stats(container_name)

@app.get("/api/containers/{container_name}/logs")
async def get_container_logs(
    container_name: str, 
    tail: int = Query(100, ge=1, le=1000, description="Number of log lines to retrieve")
):
    """Get logs from a specific container"""
    return await container.docker_handlers.get_container_logs(container_name, tail)

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

@app.post("/api/config/restart-services")
async def restart_affected_services(config_type: str = Query(..., regex="^(env|accounts)$")):
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