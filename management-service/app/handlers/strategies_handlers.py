"""
Strategies handlers for fetching available strategies from Zehnlabs Workers API
"""
import asyncio
import httpx
from typing import List, Dict, Any
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class StrategiesHandlers:
    """Handlers for strategies management"""
    
    def __init__(self):
        self.workers_api_url = "https://workers.fintech.zehnlabs.com/api/v1"
        self.timeout = 10.0
    
    async def get_strategies(self) -> List[Dict[str, Any]]:
        """Get available strategies from Zehnlabs Workers API"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.workers_api_url}/strategies")
                
                if response.status_code != 200:
                    logger.error(f"Failed to fetch strategies: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=502, 
                        detail="Failed to fetch strategies from external API"
                    )
                
                data = response.json()
                strategies = data.get("strategies", [])
                
                # Transform to simpler format for frontend
                result = []
                for strategy in strategies:
                    result.append({
                        "name": self._format_strategy_name(strategy.get("strategy_name", "")),
                        "long_name": strategy.get("strategy_name", "")
                    })
                
                # Sort by name for consistency
                result.sort(key=lambda x: x["name"])
                
                return result
                
        except httpx.TimeoutException:
            logger.error("Timeout while fetching strategies")
            raise HTTPException(status_code=504, detail="Timeout fetching strategies")
        except httpx.RequestError as e:
            logger.error(f"Request error while fetching strategies: {str(e)}")
            raise HTTPException(status_code=502, detail="Failed to connect to strategies API")
        except Exception as e:
            logger.error(f"Unexpected error fetching strategies: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    def _format_strategy_name(self, long_name: str) -> str:
        """
        Convert strategy long name to internal format
        e.g., "ETF Blend 101-15" -> "etf-blend-101-15"
        """
        if not long_name:
            return ""
            
        return long_name.lower().replace(" ", "-").replace("_", "-")