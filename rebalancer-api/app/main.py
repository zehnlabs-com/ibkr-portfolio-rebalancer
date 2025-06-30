from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional
import uvicorn
import asyncio
import nest_asyncio

from app.config import config
from app.logger import setup_logger
from app.models.requests import RebalanceRequest
from app.models.responses import (
    RebalanceResponse, AccountsResponse, AccountInfo, PositionsResponse, 
    PositionInfo, AccountValueResponse, HealthResponse, RebalanceOrder
)
from app.services.ibkr_client import IBKRClient
from app.services.rebalancer_service import RebalancerService

logger = setup_logger(__name__)

# Global instances
ibkr_client = None
rebalancer_service = None

async def maintain_ibkr_connection():
    """Background task to maintain IBKR connection"""
    while True:
        try:
            if ibkr_client and not ibkr_client.ib.isConnected():
                logger.info("IBKR connection lost, attempting to reconnect...")
                await ibkr_client.connect()
        except Exception as e:
            logger.error(f"Error in connection maintenance: {e}")
        await asyncio.sleep(30)  # Check every 30 seconds

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ibkr_client, rebalancer_service
    
    # Apply nest_asyncio to allow nested async loops
    nest_asyncio.apply()
    
    logger.info("Starting Rebalancer API service")
    
    # Initialize services
    ibkr_client = IBKRClient()
    rebalancer_service = RebalancerService(ibkr_client)
    
    # Start connection maintenance task
    maintenance_task = asyncio.create_task(maintain_ibkr_connection())
    
    yield
    
    # Cleanup
    logger.info("Shutting down Rebalancer API service")
    maintenance_task.cancel()
    if ibkr_client:
        await ibkr_client.disconnect()

def get_ibkr_client() -> IBKRClient:
    """Dependency injection for IBKR client"""
    return ibkr_client

def get_rebalancer_service() -> RebalancerService:
    """Dependency injection for rebalancer service"""
    return rebalancer_service

app = FastAPI(
    title="Portfolio Rebalancer API",
    description="REST API for portfolio rebalancing operations",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {"message": "Portfolio Rebalancer API", "version": "1.0.0"}

@app.get("/health", response_model=HealthResponse)
async def health_check(client: IBKRClient = Depends(get_ibkr_client)):
    ibkr_connected = False
    message = None
    
    try:
        if client:
            ibkr_connected = await client.ensure_connected()
        
        status = "healthy" if ibkr_connected else "unhealthy"
        if not ibkr_connected:
            message = "IBKR connection failed"
            
    except Exception as e:
        status = "unhealthy"
        message = f"Health check failed: {str(e)}"
        logger.error(f"Health check error: {e}")
    
    return HealthResponse(
        status=status,
        ibkr_connected=ibkr_connected,
        timestamp=datetime.utcnow(),
        message=message
    )

@app.get("/accounts", response_model=AccountsResponse)
async def list_accounts():
    try:
        accounts = []
        for account_config in config.accounts:
            accounts.append(AccountInfo(
                account_id=account_config.account_id,
                notification_channel=account_config.notification.channel,
                allocations_url=account_config.allocations.url
            ))
        
        return AccountsResponse(accounts=accounts)
    
    except Exception as e:
        logger.error(f"Error listing accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rebalance/{account_id}", response_model=RebalanceResponse)
async def rebalance_account(account_id: str, request: RebalanceRequest, background_tasks: BackgroundTasks):
    try:
        # Find account configuration
        account_config = config.get_account_config(account_id)
        if not account_config:
            raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
        
        # Ensure IBKR connection
        if not await ibkr_client.ensure_connected():
            raise HTTPException(status_code=503, detail="Unable to connect to IBKR")
        
        # Determine execution mode
        is_dry_run = request.execution_mode != "rebalance"
        
        # Execute rebalancing
        orders = await rebalancer_service.rebalance_account(account_config, dry_run=is_dry_run)
        
        # Convert orders to response format
        response_orders = []
        for order in orders:
            response_orders.append(RebalanceOrder(
                symbol=order.symbol,
                quantity=order.quantity,
                action=order.action,
                market_value=order.market_value
            ))
        
        mode_text = "dry_run" if is_dry_run else "live"
        
        return RebalanceResponse(
            account_id=account_id,
            execution_mode=mode_text,
            orders=response_orders,
            status="success",
            message=f"Rebalancing completed successfully ({mode_text})",
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rebalancing account {account_id}: {e}")
        return RebalanceResponse(
            account_id=account_id,
            execution_mode=request.execution_mode,
            orders=[],
            status="error",
            message=str(e),
            timestamp=datetime.utcnow()
        )

@app.post("/rebalance/{account_id}/dry-run", response_model=RebalanceResponse)
async def dry_run_rebalance(
    account_id: str,
    client: IBKRClient = Depends(get_ibkr_client),
    service: RebalancerService = Depends(get_rebalancer_service)
):
    try:
        account_config = config.get_account_config(account_id)
        if not account_config:
            raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
        
        if not await client.ensure_connected():
            raise HTTPException(status_code=503, detail="Unable to connect to IBKR")
        
        orders = await service.dry_run_rebalance(account_config)
        
        response_orders = []
        for order in orders:
            response_orders.append(RebalanceOrder(
                symbol=order.symbol,
                quantity=order.quantity,
                action=order.action,
                market_value=order.market_value
            ))
        
        return RebalanceResponse(
            account_id=account_id,
            execution_mode="dry_run",
            orders=response_orders,
            status="success",
            message="Dry run rebalancing completed successfully",
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in dry run rebalance for account {account_id}: {e}")
        return RebalanceResponse(
            account_id=account_id,
            execution_mode="dry_run",
            orders=[],
            status="error",
            message=str(e),
            timestamp=datetime.utcnow()
        )

@app.get("/accounts/{account_id}/positions", response_model=PositionsResponse)
async def get_account_positions(account_id: str, client: IBKRClient = Depends(get_ibkr_client)):
    try:
        account_config = config.get_account_config(account_id)
        if not account_config:
            raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
        
        if not await client.ensure_connected():
            raise HTTPException(status_code=503, detail="Unable to connect to IBKR")
        
        positions_data = await client.get_positions(account_id)
        
        positions = []
        for pos in positions_data:
            positions.append(PositionInfo(
                symbol=pos['symbol'],
                position=pos['position'],
                market_value=pos['market_value'],
                avg_cost=pos['avg_cost']
            ))
        
        return PositionsResponse(
            account_id=account_id,
            positions=positions,
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting positions for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/accounts/{account_id}/value", response_model=AccountValueResponse)
async def get_account_value(account_id: str, client: IBKRClient = Depends(get_ibkr_client)):
    try:
        account_config = config.get_account_config(account_id)
        if not account_config:
            raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
        
        if not await client.ensure_connected():
            raise HTTPException(status_code=503, detail="Unable to connect to IBKR")
        
        account_value = await client.get_account_value(account_id)
        
        return AccountValueResponse(
            account_id=account_id,
            net_liquidation=account_value,
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting account value for {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.api.host,
        port=config.api.port,
        workers=config.api.workers,
        log_level=config.log_level.lower(),
        loop="asyncio"  # Use asyncio instead of uvloop to allow nest_asyncio patching
    )