from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routers import portfolio
from app.config import Settings
from app.services.ibkr_service import get_ibkr_service
import uvicorn
from loguru import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage IBKR service lifecycle"""
    settings = Settings()
    ibkr_service = get_ibkr_service(settings)
    
    # Startup
    logger.info("Starting IBKR Portfolio Rebalancer...")
    await ibkr_service.start_service()
    
    yield
    
    # Shutdown
    logger.info("Shutting down IBKR Portfolio Rebalancer...")
    await ibkr_service.stop_service()

def create_app() -> FastAPI:
    app = FastAPI(
        title="IBKR Portfolio Rebalancer",
        description="FastAPI service for Interactive Brokers portfolio rebalancing",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(portfolio.router)
    
    return app

app = create_app()


if __name__ == "__main__":
    settings = Settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level=settings.log_level.lower(),
        reload=True,
        loop="asyncio"  # Force asyncio instead of uvloop
    )