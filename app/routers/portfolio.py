# app/routers/portfolio.py
from fastapi import APIRouter, HTTPException, Depends
from app.models import RebalanceRequest, RebalanceResponse, CalculateResponse
from app.services.rebalancer import PortfolioRebalancer
from app.services.ibkr_service import get_ibkr_service, IBKRService
from app.config import Settings
from loguru import logger
from functools import lru_cache

router = APIRouter(prefix="/api/v1", tags=["portfolio"])

@lru_cache()
def get_settings():
    """Cached settings"""
    return Settings()

def get_ibkr_service_dep() -> IBKRService:
    """Get IBKR service singleton for dependency injection"""
    from app.services.ibkr_service import get_ibkr_service
    return get_ibkr_service()

def get_rebalancer():
    """Get rebalancer with IBKR service"""
    ibkr_service = get_ibkr_service_dep()
    return PortfolioRebalancer(ibkr_service)

@router.post("/calculate", response_model=CalculateResponse)
async def calculate_rebalance_orders(
    request: RebalanceRequest,
    rebalancer: PortfolioRebalancer = Depends(get_rebalancer)
):
    """Calculate orders without executing them"""
    try:
        result = await rebalancer.calculate_orders(request.allocations)
        return CalculateResponse(**result)
    except Exception as e:
        logger.error(f"Error in calculate endpoint: {str(e)}")
        error_msg = str(e)
        if "Not connected to IBKR" in error_msg:
            raise HTTPException(
                status_code=503, 
                detail="IBKR connection not available. Check /connection/status for details."
            )
        elif "Unable to connect to IBKR" in error_msg:
            raise HTTPException(
                status_code=503, 
                detail="IBKR connection failed. Please ensure IBKR Gateway is running and accessible."
            )
        elif "Failed to get" in error_msg:
            raise HTTPException(
                status_code=502, 
                detail=f"IBKR data error: {error_msg}"
            )
        else:
            raise HTTPException(status_code=500, detail=f"Portfolio calculation failed: {error_msg}")

@router.post("/rebalance", response_model=RebalanceResponse)
async def rebalance_portfolio(
    request: RebalanceRequest,
    rebalancer: PortfolioRebalancer = Depends(get_rebalancer)
):
    """Execute portfolio rebalancing"""
    try:
        result = await rebalancer.execute_rebalance(request.allocations)
        return RebalanceResponse(**result)
    except Exception as e:
        logger.error(f"Error in rebalance endpoint: {str(e)}")
        error_msg = str(e)
        if "Not connected to IBKR" in error_msg:
            raise HTTPException(
                status_code=503, 
                detail="IBKR connection not available. Check /connection/status for details."
            )
        elif "Unable to connect to IBKR" in error_msg:
            raise HTTPException(
                status_code=503, 
                detail="IBKR connection failed. Please ensure IBKR Gateway is running and accessible."
            )
        elif "Failed to place order" in error_msg:
            raise HTTPException(
                status_code=502, 
                detail=f"Order execution failed: {error_msg}"
            )
        elif "Failed to get" in error_msg:
            raise HTTPException(
                status_code=502, 
                detail=f"IBKR data error: {error_msg}"
            )
        else:
            raise HTTPException(status_code=500, detail=f"Portfolio rebalancing failed: {error_msg}")

@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "service": "IBKR Portfolio Rebalancer"}

@router.get("/connection/status")
async def connection_status():
    """Check IBKR connection status"""
    try:
        ibkr_service = get_ibkr_service_dep()
        is_connected = ibkr_service.is_connected()
        
        return {
            "connected": is_connected,
            "status": "connected" if is_connected else "disconnected",
            "message": "IBKR connection is active" if is_connected else "IBKR connection is not available"
        }
    except Exception as e:
        logger.error(f"Error checking connection status: {str(e)}")
        return {
            "connected": False,
            "status": "error",
            "message": f"Connection status check failed: {str(e)}"
        }

@router.get("/account/info")
async def get_account_info():
    """Get account information"""
    try:
        ibkr_service = get_ibkr_service_dep()
        
        account_value = await ibkr_service.get_account_value()
        positions = await ibkr_service.get_positions()
        
        return {
            "success": True,
            "account_value": account_value,
            "positions": positions,
            "position_count": len(positions)
        }
    except Exception as e:
        logger.error(f"Error getting account info: {str(e)}")
        error_msg = str(e)
        if "Not connected to IBKR" in error_msg:
            raise HTTPException(
                status_code=503, 
                detail="IBKR connection not available. Check /connection/status for details."
            )
        elif "Unable to connect to IBKR" in error_msg:
            raise HTTPException(
                status_code=503, 
                detail="IBKR connection failed. Please ensure IBKR Gateway is running and accessible."
            )
        elif "Failed to get" in error_msg:
            raise HTTPException(
                status_code=502, 
                detail=f"IBKR data error: {error_msg}"
            )
        else:
            raise HTTPException(status_code=500, detail=f"Account info retrieval failed: {error_msg}")