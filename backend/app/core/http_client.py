import httpx
import logging

logger = logging.getLogger(__name__)

class GlobalHTTPClient:
    def __init__(self):
        self.client: httpx.AsyncClient = None

    def start(self):
        logger.info("Initializing Global HTTP Client")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def stop(self):
        if self.client:
            logger.info("Closing Global HTTP Client")
            await self.client.aclose()
            self.client = None

http_client = GlobalHTTPClient()
