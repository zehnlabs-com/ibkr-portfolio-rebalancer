from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import portfolio
from app.config import Settings
import uvicorn
from loguru import logger

def create_app() -> FastAPI:
    app = FastAPI(
        title="IBKR Portfolio Rebalancer",
        description="FastAPI service for Interactive Brokers portfolio rebalancing",
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
    
    # Include routers
    app.include_router(portfolio.router)
    
    return app

app = create_app()

@app.on_event("startup")
async def startup_event():
    logger.info("IBKR Portfolio Rebalancer API starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("IBKR Portfolio Rebalancer API shutting down...")

if __name__ == "__main__":
    settings = Settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level=settings.log_level.lower(),
        reload=True
    )