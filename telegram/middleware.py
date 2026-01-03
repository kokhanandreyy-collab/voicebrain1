import asyncio
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message
from cachetools import TTLCache

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, slow_mode_delay: float = 1.0):
        self.cache = TTLCache(maxsize=10000, ttl=slow_mode_delay)
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id
        if user_id in self.cache:
            return await event.answer("⚠️ please don't spam! Slow down a bit.")

        self.cache[user_id] = True
        return await handler(event, data)
