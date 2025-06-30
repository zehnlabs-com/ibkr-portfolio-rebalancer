"""
HTTP client for communicating with the Rebalancer API Service
"""
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from app.logger import setup_logger
from app.config import config

logger = setup_logger(__name__)


class RebalancerClient:
    """HTTP client for the Rebalancer API service"""
    
    def __init__(self, base_url: str = None, timeout: int = None):
        self.base_url = base_url or config.REBALANCER_API_URL
        self.timeout = timeout or config.REBALANCER_API_TIMEOUT
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
        
    async def connect(self):
        """Initialize the HTTP session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info(f"Connected to Rebalancer API at {self.base_url}")
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Closed Rebalancer API connection")
    
    async def health_check(self) -> bool:
        """
        Check if the rebalancer service is healthy
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            await self.connect()
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    is_healthy = data.get('status') == 'healthy'
                    logger.debug(f"Health check result: {is_healthy}")
                    return is_healthy
                else:
                    logger.warning(f"Health check failed with status: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def trigger_rebalance(self, account_id: str, execution_mode: str = "dry_run") -> Dict[str, Any]:
        """
        Trigger rebalancing for a specific account
        
        Args:
            account_id: The account ID to rebalance
            execution_mode: "dry_run" for simulation, "rebalance" for live execution
            
        Returns:
            Rebalance response data
            
        Raises:
            Exception: If the API call fails
        """
        try:
            await self.connect()
            
            endpoint = f"/rebalance/{account_id}"
            if execution_mode == "dry_run":
                endpoint += "/dry-run"
            
            payload = {
                "execution_mode": execution_mode
            }
            
            logger.info(f"Triggering {execution_mode} rebalance for account {account_id}")
            
            async with self.session.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                response_data = await response.json()
                
                if response.status == 200:
                    logger.info(f"Rebalance completed successfully for account {account_id}")
                    return response_data
                else:
                    error_msg = f"Rebalance failed for account {account_id}: {response.status} - {response_data}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                    
        except Exception as e:
            logger.error(f"Failed to trigger rebalance for account {account_id}: {e}")
            raise
    
    async def get_accounts(self) -> Dict[str, Any]:
        """
        Get list of configured accounts
        
        Returns:
            Accounts data
            
        Raises:
            Exception: If the API call fails
        """
        try:
            await self.connect()
            
            async with self.session.get(f"{self.base_url}/accounts") as response:
                
                response_data = await response.json()
                
                if response.status == 200:
                    logger.debug("Retrieved accounts list successfully")
                    return response_data
                else:
                    error_msg = f"Failed to get accounts: {response.status} - {response_data}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                    
        except Exception as e:
            logger.error(f"Failed to get accounts: {e}")
            raise
    
    async def get_account_positions(self, account_id: str) -> Dict[str, Any]:
        """
        Get current positions for an account
        
        Args:
            account_id: The account ID
            
        Returns:
            Account positions data
            
        Raises:
            Exception: If the API call fails
        """
        try:
            await self.connect()
            
            async with self.session.get(f"{self.base_url}/accounts/{account_id}/positions") as response:
                
                response_data = await response.json()
                
                if response.status == 200:
                    logger.debug(f"Retrieved positions for account {account_id}")
                    return response_data
                else:
                    error_msg = f"Failed to get positions for account {account_id}: {response.status} - {response_data}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                    
        except Exception as e:
            logger.error(f"Failed to get positions for account {account_id}: {e}")
            raise
    
    async def get_account_value(self, account_id: str) -> Dict[str, Any]:
        """
        Get account value
        
        Args:
            account_id: The account ID
            
        Returns:
            Account value data
            
        Raises:
            Exception: If the API call fails
        """
        try:
            await self.connect()
            
            async with self.session.get(f"{self.base_url}/accounts/{account_id}/value") as response:
                
                response_data = await response.json()
                
                if response.status == 200:
                    logger.debug(f"Retrieved account value for account {account_id}")
                    return response_data
                else:
                    error_msg = f"Failed to get account value for account {account_id}: {response.status} - {response_data}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                    
        except Exception as e:
            logger.error(f"Failed to get account value for account {account_id}: {e}")
            raise