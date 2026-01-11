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

    def _generate_key(self, prefix: str, data: str, scope: str = "general") -> str:
        """Generates a stable cache key based on data hash and scope."""
        data_hash = hashlib.sha256(data.encode()).hexdigest()
        return f"cache:ai:{prefix}:{scope}:{data_hash}"

    async def get_analysis(self, text: str, scope: str = "general") -> Optional[Dict[str, Any]]:
        """Retrieves cached analysis result if exists."""
        if not self.redis: return None
        try:
            key = self._generate_key("analysis", text, scope)
            data = await self.redis.get(key)
            if data:
                logger.info(f"Cache Hit ({scope})")
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
            return None

    async def save_analysis(self, text: str, result: Dict[str, Any], scope: str = "general"):
        """Saves analysis result to cache."""
        if not self.redis: return
        try:
            # Inject scope metadata for transparency transparency
            result["_cache_scope"] = scope
            
            key = self._generate_key("analysis", text, scope)
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

    def generate_smart_key(self, content_hash: str, identity_version: str, context_hash: str = "") -> str:
        """
        Generates a robust hash key for complex content (e.g. reflection).
        Key = Hash( content_hash + identity_version + context_hash )
        """
        raw = f"{content_hash}|{identity_version}|{context_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def save_embedding(self, text: str, embedding: list):
        """Saves embedding to cache."""
        if not self.redis: return
        try:
            key = self._generate_key("embedding", text)
            await self.redis.setex(key, self.ttl, json.dumps(embedding))
        except Exception as e:
            logger.warning(f"Embedding cache save failed: {e}")
