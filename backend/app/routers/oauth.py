from fastapi import APIRouter, HTTPException, Depends, Request
from app.core.limiter import limiter
from fastapi.responses import RedirectResponse
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from datetime import timedelta
import os
from app.core.database import get_db, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, VK_CLIENT_ID, VK_CLIENT_SECRET, MAILRU_CLIENT_ID, MAILRU_CLIENT_SECRET, TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET
from app.models import User
from app.core.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
import uuid

router = APIRouter()

# Configuration mapping
PROVIDERS = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_info_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "scope": "openid email profile"
    },
    "vk": {
        "auth_url": "https://oauth.vk.com/authorize",
        "token_url": "https://oauth.vk.com/access_token",
        "user_info_url": "https://api.vk.com/method/users.get",
        "client_id": VK_CLIENT_ID,
        "client_secret": VK_CLIENT_SECRET,
        "scope": "email"
    },
    "mailru": {
        "auth_url": "https://oauth.mail.ru/login",
        "token_url": "https://oauth.mail.ru/token",
        "user_info_url": "https://oauth.mail.ru/userinfo",
        "client_id": MAILRU_CLIENT_ID,
        "client_secret": MAILRU_CLIENT_SECRET,
        "scope": "userinfo"
    },
    "twitter": {
        "auth_url": "https://twitter.com/i/oauth2/authorize",
        "token_url": "https://api.twitter.com/2/oauth2/token",
        "user_info_url": "https://api.twitter.com/2/users/me",
        "client_id": TWITTER_CLIENT_ID,
        "client_secret": TWITTER_CLIENT_SECRET,
        "scope": "users.read tweet.read",
        "extra_params": {"code_challenge": "challenge", "code_challenge_method": "plain"} # Simplification for demo
    }
}

from app.core.config import settings

@router.get("/{provider}/login")
async def login_via_provider(provider: str):
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="Provider not supported")
    
    cfg = PROVIDERS[provider]
    redirect_uri = f"{settings.API_BASE_URL}/api/v1/auth/{provider}/callback"
    
    # --- MOCK MODE (If keys are missing) ---
    if not cfg["client_id"]:
        # Return a redirect to our own callback with a magic code
        return RedirectResponse(f"{redirect_uri}?code=mock_dev_code")
        
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": cfg["scope"],
        "state": "random_state_string"
    }
    
    if "extra_params" in cfg:
        params.update(cfg["extra_params"])
        
    # Build query string manually to avoid urllib quote issues depending on provider quirks
    import urllib.parse
    url = cfg["auth_url"] + "?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)

@router.get("/{provider}/callback")
@limiter.limit("50/minute")
async def auth_callback(request: Request, provider: str, code: str, db: AsyncSession = Depends(get_db)):
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="Provider not found")
        
    cfg = PROVIDERS[provider]
    redirect_uri = f"{REDIRECT_URI_BASE}/{provider}/callback"
    
    user_email = None

    # --- MOCK MODE HANDLE ---
    if code == "mock_dev_code":
        import random
        user_email = f"mock_{provider}_{random.randint(1000,9999)}@example.com"
        # Skip HTTP calls
    
    else:
        # 1. Exchange Code for Token
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            }
            
            # Twitter specific
            if provider == "twitter":
                 data["code_verifier"] = "challenge"

            response = await client.post(cfg["token_url"], data=data)
            token_data = response.json()
            
            if "error" in token_data:
                raise HTTPException(status_code=400, detail=f"OAuth Error: {token_data.get('error_description', token_data)}")

            access_token = token_data.get("access_token")
            
            # 2. Get User Info
            if provider == "google":
                user_info_resp = await client.get(cfg["user_info_url"], headers={"Authorization": f"Bearer {access_token}"})
                user_info = user_info_resp.json()
                user_email = user_info.get("email")
                
            elif provider == "mailru":
                 user_info_resp = await client.get(cfg["user_info_url"], params={"access_token": access_token})
                 user_info = user_info_resp.json()
                 user_email = user_info.get("email")
                 
            elif provider == "vk":
                # VK is weird, email might come in the token response itself or user info
                user_email = token_data.get("email") 
                if not user_email:
                     user_id = token_data.get("user_id")
                     user_email = f"vk_{user_id}@vk.placeholder"

            elif provider == "twitter":
                 # Twitter v2 /me doesn't return email by default without special permissions
                 user_email = f"twitter_user@twitter.placeholder"

    if not user_email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from provider")

    # 3. Create or Update User
    result = await db.execute(select(User).where(User.email == user_email))
    db_user = result.scalars().first()
    
    if not db_user:
        db_user = User(
            email=user_email,
            hashed_password=None, # OAuth users don't have passwords
            oauth_accounts={provider: "linked"}
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
    else:
        # Update existing user to link this provider if not linked
        current_accounts = db_user.oauth_accounts or {}
        if provider not in current_accounts:
            current_accounts[provider] = "linked"
            db_user.oauth_accounts = current_accounts
            # Force update (SQLAlchemy sometimes misses JSON updates)
            # In asyncpg/sqlalchemy syncing json changes can be tricky, re-assigning often helps
            from sqlalchemy import update
            await db.execute(update(User).where(User.id == db_user.id).values(oauth_accounts=current_accounts))
            await db.commit()

    # 4. Create Session Token (Our JWT)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    my_access_token = create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    
    # Redirect back to frontend with token in URL param
    # In prod, better to use a secure cookie or an intermediate page
    return RedirectResponse(f"http://localhost:5173/dashboard?token={my_access_token}")
