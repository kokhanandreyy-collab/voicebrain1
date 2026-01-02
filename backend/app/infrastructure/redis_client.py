import json
from typing import List, Dict, Any, Optional
import redis.asyncio as redis
from app.infrastructure.config import settings

class ShortTermMemory:
    """
    Manages user short-term memory (last messages/actions) in Redis.
    Structure: Redis List "user:{user_id}:short_term"
    TTL: 3600 seconds
    """
    def __init__(self):
        self._redis = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        self.ttl = 3600
        self.max_size = 10

    async def add_action(self, user_id: str, action_data: Dict[str, Any]):
        """Adds an action to the user's short-term history."""
        key = f"user:{user_id}:short_term"
        
        # Add to head of list
        await self._redis.lpush(key, json.dumps(action_data))
        
        # Trim to max size
        await self._redis.ltrim(key, 0, self.max_size - 1)
        
        # Set/Refresh TTL
        await self._redis.expire(key, self.ttl)

    async def get_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieves the full short-term history for a user."""
        key = f"user:{user_id}:short_term"
        items = await self._redis.lrange(key, 0, -1)
        return [json.loads(i) for i in items]

    async def clear(self, user_id: str):
        """Clears short-term memory for a user."""
        key = f"user:{user_id}:short_term"
        await self._redis.delete(key)

short_term_memory = ShortTermMemory()
