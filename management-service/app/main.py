"""
Management Service FastAPI Application - SOLID Principles Implementation
"""
import logging
from typing import List
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware

from app.container import container
from app.models.queue_models import QueueStatus, QueueEvent, AddEventRequest, AddEventResponse, RemoveEventResponse
from app.models.health_models import HealthStatus, DetailedHealthStatus
from app.config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Portfolio Rebalancer Management Service",
    description="Queue management and health monitoring for the portfolio rebalancer system",
    version="1.0.0"
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
    return {"message": "Portfolio Rebalancer Management Service", "version": "1.0.0"}

# Health endpoints (public)
@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint"""
    return await container.health_handlers.health_check()

@app.get("/health/detailed", response_model=DetailedHealthStatus)
async def detailed_health_check():
    """Detailed health check endpoint"""
    return await container.health_handlers.detailed_health_check()

# Queue status endpoints (public)
@app.get("/queue/status", response_model=QueueStatus)
async def get_queue_status():
    """Get queue status"""
    return await container.queue_handlers.get_queue_status()

@app.get("/queue/events", response_model=List[QueueEvent])
async def get_queue_events(limit: int = Query(100, ge=1, le=1000)):
    """Get events from queue"""
    return await container.queue_handlers.get_queue_events(limit=limit)

# Queue management endpoints (require API key)
@app.delete("/queue/events/{event_id}", response_model=RemoveEventResponse)
async def remove_event(
    event_id: str,
    api_key: str = Depends(container.auth_middleware.verify_api_key)
):
    """Remove event from queue (requires API key)"""
    return await container.queue_handlers.remove_event(event_id, api_key)

@app.post("/queue/events", response_model=AddEventResponse)
async def add_event(
    event_request: AddEventRequest,
    api_key: str = Depends(container.auth_middleware.verify_api_key)
):
    """Add event to queue (requires API key)"""
    return await container.queue_handlers.add_event(event_request, api_key)

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