from fastapi import FastAPI, APIRouter, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import traceback
import sentry_sdk
import structlog
from prometheus_fastapi_instrumentator import Instrumentator

from infrastructure.http_client import http_client
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from infrastructure.rate_limit import limiter
from infrastructure.config import settings
from infrastructure.logging import configure_logging
from infrastructure.monitoring import monitor
from infrastructure.database import engine
from sqlalchemy import event

from app.api.middleware.rate_limit import RateLimitMiddleware
from app.api.middleware.auth import AuthMiddleware
from app.api.middleware.logging_middleware import LoggingMiddleware

# Initialize Structured Logging
configure_logging()
logger = structlog.get_logger()

app = FastAPI(
    title="VoiceBrain API",
    description="Backend API for VoiceBrain - The Adaptive AI Voice Assistant.",
    version="1.1.0"
)

# 1. Strict CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Process-Time-MS"],
)

# 2. Middleware Stack (Order Matters)
# Logging wrap everything to capture latency and errors
app.add_middleware(LoggingMiddleware)
# Auth populates request.state.user_id for rate limiter and logger
app.add_middleware(AuthMiddleware)
# Rate limiting uses the populated user_id or IP
app.add_middleware(RateLimitMiddleware)

app.state.limiter = limiter

# --- Global Exception Handlers ---

@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "code": "rate_limit_exceeded",
            "message": "Too many requests. Please slow down.",
            "retry_after": exc.detail
        },
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": "api_error",
            "message": exc.detail
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": "validation_error",
            "message": "The request data is invalid.",
            "details": exc.errors()
        },
    )

@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    # Log the full error for internal tracking
    logger.error("unhandled_exception", error=str(exc), traceback=traceback.format_exc())
    
    # Hide internal details from user in production
    message = "An internal server error occurred."
    if settings.ENVIRONMENT == "development":
        message = str(exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "internal_error",
            "message": message
        },
    )

# Track DB queries
@event.listens_for(engine.sync_engine, "before_cursor_execute")
def count_db_query(conn, cursor, statement, parameters, context, executemany):
    monitor.track_db_query()

Instrumentator().instrument(app).expose(app)

@app.on_event("startup")
async def startup():
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            environment=settings.ENVIRONMENT
        )

    http_client.start()

    import redis.asyncio as redis
    from fastapi_limiter import FastAPILimiter
    try:
        redis_connection = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(redis_connection)
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))

@app.on_event("shutdown")
async def shutdown():
    await http_client.stop()

# --- Router Configuration ---
from app.api.routers.v1 import (
    notes, integrations, exports, payment, 
    oauth, auth, tags, notifications, 
    feedback, admin, users, settings as user_settings
)

api_v1_router = APIRouter()
api_v1_router.include_router(auth.router, prefix="/auth")
api_v1_router.include_router(oauth.router, prefix="/auth")
api_v1_router.include_router(notes.router, prefix="/notes")
api_v1_router.include_router(integrations.router, prefix="/integrations")
api_v1_router.include_router(exports.router, prefix="/export")
api_v1_router.include_router(payment.router, prefix="/payment")
api_v1_router.include_router(tags.router, prefix="/tags")
api_v1_router.include_router(notifications.router, prefix="/notifications")
api_v1_router.include_router(feedback.router, prefix="/feedback")
api_v1_router.include_router(admin.router, prefix="/admin")
api_v1_router.include_router(users.router, prefix="/users")
api_v1_router.include_router(user_settings.router, prefix="/user/settings")

app.include_router(api_v1_router, prefix="/api/v1")

@app.get("/")
@limiter.exempt
async def root():
    return {"message": "VoiceBrain API v1", "environment": settings.ENVIRONMENT}

@app.get("/health")
@limiter.exempt
async def health():
    return {"status": "ok"}
