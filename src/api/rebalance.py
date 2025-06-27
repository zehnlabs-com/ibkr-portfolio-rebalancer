from fastapi import APIRouter, HTTPException, Depends
from typing import List
from decimal import Decimal
from ..models.portfolio import AllocationRequest, RebalanceResponse
from ..services.ibkr_client import IBKRClient
from ..services.rebalancer import PortfolioRebalancer

router = APIRouter()


async def get_ibkr_client() -> IBKRClient:
    """Dependency to get IBKR client"""
    return IBKRClient()


async def get_rebalancer(ibkr_client: IBKRClient = Depends(get_ibkr_client)) -> PortfolioRebalancer:
    """Dependency to get portfolio rebalancer"""
    return PortfolioRebalancer(ibkr_client)


@router.post("/rebalance", response_model=RebalanceResponse)
async def rebalance_portfolio(
    allocations: List[AllocationRequest],
    execute: bool = False,
    portfolio_cap: str = None,
    rebalancer: PortfolioRebalancer = Depends(get_rebalancer)
) -> RebalanceResponse:
    """
    Rebalance portfolio based on target allocations using johnnymo87's exact algorithm
    
    - **allocations**: List of target allocations with symbol and percentage (must sum to exactly 1.0)
    - **execute**: Whether to execute trades (default: False for dry-run)
    - **portfolio_cap**: Optional portfolio cap (e.g., "$50000" or "80%")
    """
    
    # Validate allocations sum to exactly 1.0 (johnnymo87's strict validation)
    total_allocation = sum(alloc.allocation for alloc in allocations)
    if abs(total_allocation - Decimal('1.0')) > Decimal('0.0001'):
        raise HTTPException(
            status_code=400,
            detail=f"Allocations must sum to exactly 1.0, got {total_allocation}"
        )
    
    try:
        # Create rebalancer with portfolio cap if specified
        if portfolio_cap:
            rebalancer.portfolio_cap = portfolio_cap
        
        if execute:
            result = await rebalancer.execute_rebalance(allocations)
        else:
            result = await rebalancer.calculate_rebalance(allocations)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        await rebalancer.ibkr_client.close()


@router.get("/positions")
async def get_positions(ibkr_client: IBKRClient = Depends(get_ibkr_client)):
    """Get current portfolio positions with precise decimal values"""
    try:
        positions = await ibkr_client.get_positions()
        total_value = await ibkr_client.get_portfolio_value()
        
        # Calculate current allocations
        allocations = {}
        if total_value > 0:
            for position in positions:
                allocations[position.symbol] = {
                    "quantity": position.quantity,
                    "market_value": position.market_value,
                    "allocation_percent": (position.market_value / total_value * Decimal('100')).quantize(Decimal('0.01'))
                }
        
        return {
            "positions": positions,
            "total_portfolio_value": total_value,
            "current_allocations": allocations
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        await ibkr_client.close()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}