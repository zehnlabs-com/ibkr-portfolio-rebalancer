# app/routers/portfolio.py
from fastapi import APIRouter, HTTPException, Depends
from app.models import RebalanceRequest, RebalanceResponse, CalculateResponse
from app.services.rebalancer import PortfolioRebalancer
from app.services.ibkr_client import IBKRClient
from app.config import Settings
from loguru import logger
from functools import lru_cache

router = APIRouter(prefix="/api/v1", tags=["portfolio"])

@lru_cache()
def get_settings():
    """Cached settings"""
    return Settings()

def get_ibkr_client():
    """Get IBKR client - synchronous"""
    settings = get_settings()
    return IBKRClient(settings)

def get_rebalancer():
    """Get rebalancer with connected client"""
    ibkr_client = get_ibkr_client()
    return PortfolioRebalancer(ibkr_client)

@router.post("/calculate", response_model=CalculateResponse)
async def calculate_rebalance_orders(
    request: RebalanceRequest,
    rebalancer: PortfolioRebalancer = Depends(get_rebalancer)
):
    """Calculate orders without executing them"""
    try:
        result = rebalancer.calculate_orders(request.allocations)
        return CalculateResponse(**result)
    except Exception as e:
        logger.error(f"Error in calculate endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rebalance", response_model=RebalanceResponse)
async def rebalance_portfolio(
    request: RebalanceRequest,
    rebalancer: PortfolioRebalancer = Depends(get_rebalancer)
):
    """Execute portfolio rebalancing"""
    try:
        result = rebalancer.execute_rebalance(request.allocations)
        return RebalanceResponse(**result)
    except Exception as e:
        logger.error(f"Error in rebalance endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "service": "IBKR Portfolio Rebalancer"}

@router.get("/account/info")
async def get_account_info():
    """Get account information"""
    try:
        ibkr_client = get_ibkr_client()
        
        account_value = ibkr_client.get_account_value()
        positions = ibkr_client.get_positions()
        
        return {
            "success": True,
            "account_value": account_value,
            "positions": positions,
            "position_count": len(positions)
        }
    except Exception as e:
        logger.error(f"Error getting account info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))