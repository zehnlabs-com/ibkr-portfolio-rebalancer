"""
Management Service FastAPI Application - SOLID Principles Implementation
"""
import logging
import os
from typing import List
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.container import container
from app.models.queue_models import QueueStatus, QueueEvent, AddEventRequest, AddEventResponse, RemoveEventResponse, ClearQueuesResponse
from app.models.health_models import DetailedHealthStatus
from app.models.setup_models import SaveAccountsRequest, SaveAccountsResponse, AccountsDataResponse, SaveEnvRequest, SaveEnvResponse, EnvDataResponse, SetupStatusResponse, CompleteSetupResponse
from app.config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# Setup endpoints
@app.get("/setup", response_class=HTMLResponse)
async def get_main_setup_page():
    """Get the main setup page with task status"""
    return await container.setup_handlers.get_main_setup_page()

@app.get("/setup/status", response_model=SetupStatusResponse)
async def get_setup_status():
    """Get setup completion status"""
    return await container.setup_handlers.get_setup_status()

@app.get("/setup/accounts", response_class=HTMLResponse)
async def get_setup_page():
    """Get the accounts setup page"""
    return await container.setup_handlers.get_setup_page()

@app.get("/setup/accounts/data", response_model=AccountsDataResponse)
async def get_accounts_data():
    """Get current accounts configuration data"""
    return await container.setup_handlers.get_accounts_data()

@app.post("/setup/accounts", response_model=SaveAccountsResponse)
async def save_accounts(request: SaveAccountsRequest):
    """Save accounts configuration"""
    return await container.setup_handlers.save_accounts(request.dict())

@app.get("/setup/env", response_class=HTMLResponse)
async def get_env_setup_page():
    """Get the environment variables setup page"""
    return await container.setup_handlers.get_env_setup_page()

@app.get("/setup/env/data", response_model=EnvDataResponse)
async def get_env_data():
    """Get current environment variables data"""
    return await container.setup_handlers.get_env_data()

@app.post("/setup/env", response_model=SaveEnvResponse)
async def save_env(request: SaveEnvRequest):
    """Save environment variables"""
    return await container.setup_handlers.save_env(request.dict())

@app.post("/setup/complete", response_model=CompleteSetupResponse)
async def complete_setup():
    """Complete setup by restarting all services"""
    return await container.setup_handlers.complete_setup()

@app.get("/setup/complete", response_class=HTMLResponse)
async def get_setup_complete_page():
    """Get the setup completion success page"""
    return await container.setup_handlers.get_setup_complete_page()

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