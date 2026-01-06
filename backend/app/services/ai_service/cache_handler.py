import json
import hashlib
from typing import Optional, Any, Dict
from loguru import logger

class CacheHandler:
    """
    Handles key-value caching (Redis) for AI results and embeddings.
    """
    def __init__(self, redis_client: Any):
        self.redis = redis_client
        self.ttl = 604800  # 7 days

    def _generate_key(self, prefix: str, data: str) -> str:
        """Generates a stable cache key based on data hash."""
        data_hash = hashlib.sha256(data.encode()).hexdigest()
        return f"cache:ai:{prefix}:{data_hash}"

    async def get_analysis(self, text: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached analysis result if exists."""
        if not self.redis: return None
        try:
            key = self._generate_key("analysis", text)
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
            return None

    async def save_analysis(self, text: str, result: Dict[str, Any]):
        """Saves analysis result to cache."""
        if not self.redis: return
        try:
            key = self._generate_key("analysis", text)
            await self.redis.setex(key, self.ttl, json.dumps(result))
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    async def get_embedding(self, text: str) -> Optional[list]:
        """Retrieves cached embedding if exists."""
        if not self.redis: return None
        try:
            key = self._generate_key("embedding", text)
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning(f"Embedding cache retrieval failed: {e}")
            return None

    async def save_embedding(self, text: str, embedding: list):
        """Saves embedding to cache."""
        if not self.redis: return
        try:
            key = self._generate_key("embedding", text)
            await self.redis.setex(key, self.ttl, json.dumps(embedding))
        except Exception as e:
            logger.warning(f"Embedding cache save failed: {e}")
