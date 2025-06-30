import asyncio
import signal
import sys
from typing import List
from app.config import config
from app.logger import setup_logger
from app.services.ably_service import AblyService
from app.services.rebalancer_service import RebalancerService
from app.services.ibkr_client import IBKRClient

logger = setup_logger(__name__)

class PortfolioRebalancerApp:
    def __init__(self):
        self.ibkr_client = IBKRClient()
        self.rebalancer_service = RebalancerService(self.ibkr_client)
        self.ably_services: List[AblyService] = []
        self.running = False
    
    async def start(self):
        logger.info("Starting Portfolio Rebalancer App")
        
        try:
            await self.ibkr_client.connect()
            
            for account_config in config.accounts:
                ably_service = AblyService(
                    account_config,
                    self.rebalancer_service
                )
                self.ably_services.append(ably_service)
                await ably_service.start()
            
            self.running = True
            logger.info(f"App started with {len(self.ably_services)} account subscriptions")
            
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error starting app: {e}")
            await self.stop()
    
    async def stop(self):
        logger.info("Stopping Portfolio Rebalancer App")
        self.running = False
        
        for ably_service in self.ably_services:
            await ably_service.stop()
        
        await self.ibkr_client.disconnect()
        logger.info("App stopped")

async def main():
    app = PortfolioRebalancerApp()
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(app.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await app.start()

if __name__ == "__main__":
    asyncio.run(main())