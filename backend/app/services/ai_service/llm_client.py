from typing import Any, Optional
import datetime
from loguru import logger
from openai import AsyncOpenAI
from infrastructure.config import settings

class LLMClient:
    """
    Handles direct communication with LLM providers (DeepSeek, OpenAI).
    Includes usage tracking and logging.
    """
    def __init__(self, redis_client: Any = None):
        self.openai_key = settings.OPENAI_API_KEY
        self.deepseek_key = settings.DEEPSEEK_API_KEY
        self.deepseek_base = settings.DEEPSEEK_BASE_URL
        self.redis = redis_client
        
        # Initialize clients
        self.openai_client = AsyncOpenAI(api_key=self.openai_key) if self.openai_key else None
        self.deepseek_client = AsyncOpenAI(api_key=self.deepseek_key, base_url=self.deepseek_base) if self.deepseek_key else None

    async def get_completion(self, messages: list, model: str = "deepseek-chat", response_format: dict = None) -> Any:
        """Calls the appropriate LLM based on configuration and availability."""
        client = self.deepseek_client if self.deepseek_key and "deepseek" in model else self.openai_client
        
        if not client:
            raise RuntimeError("No LLM client configured (missing API keys).")

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            response_format=response_format,
            temperature=0.3 if response_format else 0.7
        )
        
        # Track usage
        await self._track_usage(response.usage)
        return response

    async def _track_usage(self, usage: Any) -> None:
        """Logs and tracks token usage in Redis."""
        if not usage: return
        
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens
        
        logger.info(f"DeepSeek usage: input {prompt_tokens}, output {completion_tokens}, total {total_tokens}")
        
        if self.redis:
            try:
                today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
                key = f"ai_usage:daily:{today}"
                async with self.redis.pipeline(transaction=True) as pipe:
                    await pipe.hincrby(key, "prompt_tokens", prompt_tokens)
                    await pipe.hincrby(key, "completion_tokens", completion_tokens)
                    await pipe.hincrby(key, "total_tokens", total_tokens)
                    await pipe.expire(key, 604800)
                    await pipe.execute()
            except Exception as e:
                logger.warning(f"Failed to track AI usage: {e}")
