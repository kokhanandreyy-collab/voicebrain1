import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 1. Generate or retrieve Request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # 2. Bind initial context to structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown"
        )

        try:
            # Execute request
            response = await call_next(request)
            
            # Calculate latency
            process_time = time.time() - start_time
            latency_ms = round(process_time * 1000, 2)
            
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-MS"] = str(latency_ms)
            
            # 3. Log completion (Structured JSON)
            # user_id will be included if set by AuthMiddleware in contextvars
            if request.url.path != "/health" and request.url.path != "/":
                logger.info(
                    "http_request",
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                    user_id=getattr(request.state, "user_id", None)
                )
                
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            latency_ms = round(process_time * 1000, 2)
            
            # Log failure
            logger.error(
                "http_request_failed",
                error=str(e),
                latency_ms=latency_ms,
                user_id=getattr(request.state, "user_id", None)
            )
            # Re-raise to be caught by global exception handlers
            raise e
