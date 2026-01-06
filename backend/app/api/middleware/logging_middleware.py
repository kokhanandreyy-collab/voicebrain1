import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from app.api.dependencies import get_current_user # Note: Depends doesn't work well in Middleware directly
# We typically can't easily get user inside middleware without duplicating auth logic or using the request.state set by AuthMiddleware if it exists.

logger = structlog.get_logger()

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 1. Generate Request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # 2. Bind context to structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None
        )

        try:
            response = await call_next(request)
            
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            
            # extract status
            status_code = response.status_code
            
            # Log completion
            if request.url.path != "/health": # Skip health check noise
                logger.info(
                    "Request finished",
                    status_code=status_code,
                    process_time=f"{process_time:.4f}s"
                )
                
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "Request failed",
                error=str(e),
                process_time=f"{process_time:.4f}s"
            )
            raise e
