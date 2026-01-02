from infrastructure.http_robust import RobustAsyncClient
import httpx
from loguru import logger

class GlobalHTTPClient:
    def __init__(self):
        self._raw_client: httpx.AsyncClient = None
        self.client: RobustAsyncClient = None

    def start(self):
        logger.info("Initializing Global Robust HTTP Client")
        self._raw_client = httpx.AsyncClient(timeout=30.0)
        self.client = RobustAsyncClient(self._raw_client)
    
    async def stop(self):
        if self._raw_client:
            logger.info("Closing Global HTTP Client")
            await self._raw_client.aclose()
            self._raw_client = None
            self.client = None

http_client = GlobalHTTPClient()
