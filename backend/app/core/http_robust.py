import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result,
    before_sleep_log,
)
import pybreaker
from loguru import logger
import asyncio
from typing import Any, Callable, TypeVar, Union

# --- Types ---
T = TypeVar("T")

# --- Circuit Breaker ---
# 5 errors trigger the breaker, 5 minutes pause
http_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=300)

# --- Retry Conditions ---
def is_retryable_status(response: httpx.Response) -> bool:
    """Retry on 429 (Too Many Requests) and 5xx (Server Errors)."""
    return response.status_code == 429 or 500 <= response.status_code <= 599

def is_timeout_or_network_error(exc: Exception) -> bool:
    """Retry on network errors or timeouts."""
    return isinstance(exc, (httpx.TimeoutException, httpx.ConnectError))

# --- Robust Wrapper ---
def robust_retry(max_attempts: int = 5):
    """
    Decorator for robust HTTP requests using tenacity.
    - Exponential backoff: 1s to 30s.
    - Customizable attempts.
    - Logs each attempt.
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=(
            retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)) |
            retry_if_result(is_retryable_status)
        ),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True
    )

class RobustAsyncClient:
    """
    A wrapper around httpx.AsyncClient that integrates retries and circuit breaking.
    """
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    @http_breaker
    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        Execute an HTTP request with circuit breaking and retries.
        """
        attempts = kwargs.pop("max_attempts", 5)

        @robust_retry(max_attempts=attempts)
        async def _make_request():
            logger.debug(f"HTTP {method} {url} - Attempting...")
            response = await self.client.request(method, url, **kwargs)
            return response

        return await _make_request()

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("DELETE", url, **kwargs)

    async def patch(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("PATCH", url, **kwargs)
