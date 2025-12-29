from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from app.core.http_client import http_client
import os

app = FastAPI(title="VoiceBrain API")

import os
# Secure CORS
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ...

@app.on_event("startup")
async def startup():
    # Database tables are now managed by Alembic
    # await engine.begin() ... 
    
    # Initialize Global HTTP Client
    http_client.start()

    # Rate Limiter Init
    from fastapi_limiter import FastAPILimiter
    import redis.asyncio as redis
    
    redis_url = "redis://redis:6379" # Docker DNS
    try:
        r = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        # Check connection (optional) or just init
        await FastAPILimiter.init(r)
        print("Rate Limiter initialized")
    except Exception as e:
         print(f"Rate Limiter Init Failed: {e}. Falling back to no limits.")
         
    # Telegram Bot is now run separately via run_bot.py

@app.on_event("shutdown")
async def shutdown():
    await http_client.stop()

# --- Router Configuration ---
# --- Router Configuration ---
from fastapi import Depends
from fastapi_limiter.depends import RateLimiter
from app.routers import notes, integrations, exports, payment, oauth, auth, tags, notifications, feedback, admin, users

api_router = APIRouter(dependencies=[Depends(RateLimiter(times=100, seconds=60))])

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

# Include the API router into the main app with version prefix
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "VoiceBrain API v1"}


