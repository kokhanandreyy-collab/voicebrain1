from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from infrastructure.http_client import http_client
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.api.middleware.auth import AuthMiddleware
from app.api.middleware.logging_middleware import LoggingMiddleware
from infrastructure.rate_limit import limiter
from infrastructure.config import settings
from infrastructure.logging import configure_logging
import sentry_sdk
from prometheus_fastapi_instrumentator import Instrumentator
import structlog

app = FastAPI(
    title="VoiceBrain API",
    description="Backend API for VoiceBrain - The Adaptive AI Voice Assistant.\n\nFeatures:\n- Voice Transcription & Analysis\n- RAG-based Memory System\n- Integrations (Notion, Slack, GCal)\n- Adaptive Personalization",
    version="1.0.0"
)

# Secure CORS
origins = settings.ALLOWED_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(LoggingMiddleware)

from fastapi import Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import traceback

logger = structlog.get_logger()

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": "http_error", "message": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": "validation_error", "message": "Invalid request parameters", "details": str(exc)},
    )

@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": "validation_error", "message": "Data validation failed", "details": exc.errors()},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Global exception", error=str(exc), traceback=traceback.format_exc())
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": "internal_error", "message": "An unexpected error occurred. Please try again later."},
    )

# ...

@app.on_event("startup")
async def startup():
    # 1. Logging
    configure_logging()
    
    # 2. Sentry
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            environment=settings.ENVIRONMENT
        )
        print("Sentry initialized")

    # 3. Prometheus Metrics
    Instrumentator().instrument(app).expose(app)

    # Database tables are now managed by Alembic
    # await engine.begin() ... 
    
    # Initialize Global HTTP Client
    http_client.start()

    # Initialize Redis for FastAPI Limiter
    import redis.asyncio as redis
    from fastapi_limiter import FastAPILimiter
    try:
        redis_connection = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(redis_connection)
        print("Rate Limiter (FastAPI-Limiter) connected to Redis")
    except Exception as e:
        print(f"Warning: Redis not available for Rate Limiter: {e}")

    # Rate Limiter is now handled by slowapi via middleware/limiter.py
    print("Rate Limiter (slowapi) active")
         
    # Telegram Bot is now run separately via run_bot.py

@app.on_event("shutdown")
async def shutdown():
    await http_client.stop()

# --- Router Configuration ---
# --- Router Configuration ---
from fastapi import Depends
from app.api.routers import notes, integrations, exports, payment, oauth, auth, tags, notifications, feedback, admin, users, settings

api_router = APIRouter()

# Group all routers under the API router
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(oauth.router, prefix="/auth", tags=["oauth"])
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(exports.router, prefix="/export", tags=["export"])
api_router.include_router(payment.router, prefix="/payment", tags=["payment"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(settings.router, prefix="/user/settings", tags=["settings"])

# Include the API router into the main app with version prefix
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
@limiter.exempt
async def root():
    return {"message": "VoiceBrain API v1"}

@app.get("/health")
@limiter.exempt
async def health():
    return {"status": "ok"}


