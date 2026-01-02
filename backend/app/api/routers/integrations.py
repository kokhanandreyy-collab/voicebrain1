from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from typing import List, Optional
from pydantic import BaseModel

from infrastructure.database import get_db
from app.models import User, Integration
from app.schemas import IntegrationCreate, IntegrationResponse
from app.api.dependencies import get_current_user

router = APIRouter(
    prefix="/integrations",
    tags=["integrations"]
)

def mask_settings(settings: dict) -> dict:
    """Mask sensitive keys in settings."""
    if not settings:
        return {}
    masked = settings.copy()
    sensitive_keys = {'api_key', 'token', 'password', 'secret', 'key'}
    for k, v in masked.items():
        if any(s in k.lower() for s in sensitive_keys) and isinstance(v, str):
            masked[k] = '****' + v[-4:] if len(v) > 4 else '****'
    return masked

@router.get("", response_model=List[IntegrationResponse])
async def get_integrations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    
    result = await db.execute(select(Integration).where(Integration.user_id == current_user.id))
    integrations = result.scalars().all()
    
    # Map to schema manually or use Pydantic with property
    response = []
    for i in integrations:
        settings = i.settings or {}
        response.append({
            "id": i.id,
            "provider": i.provider,
            "created_at": i.created_at,
            "is_active": True, # Or check expiry
            "masked_settings": mask_settings(settings),
            "status": settings.get("status", "active"),
            "error_message": settings.get("error_message")
        })
    return response

@router.get("/config")
async def get_integrations_config():
    """
    Returns the list of available integration providers and their metadata.
    This allows the frontend to be dynamic.
    """
    return [
        { "id": 'notion', "name": 'Notion', "category": "Notes", "desc": 'Save voice notes to your Notion database.', "bg": 'bg-slate-100', "text": 'text-slate-700', "icon": 'N' },
        { "id": 'slack', "name": 'Slack', "category": "Communication", "desc": 'Send summaries to your team channel.', "bg": 'bg-fuchsia-100', "text": 'text-fuchsia-600', "icon": 'S' },
        { "id": 'todoist', "name": 'Todoist', "category": "Tasks", "desc": 'Auto-create tasks from action items.', "bg": 'bg-red-50', "text": 'text-red-600', "icon": 'T' },
        { "id": 'readwise', "name": 'Readwise', "category": "Notes", "desc": 'Sync highlights to your second brain.', "bg": 'bg-yellow-50', "text": 'text-yellow-600', "icon": 'R' },
        { "id": 'zapier', "name": 'Zapier', "category": "Communication", "desc": 'Connect to 5000+ apps via Webhook.', "bg": 'bg-orange-50', "text": 'text-orange-600', "icon": 'Z', "isPremium": True },
        { "id": 'google_calendar', "name": 'Google Calendar', "category": "Tasks", "desc": 'Create events directly from voice.', "bg": 'bg-blue-50', "text": 'text-blue-600', "icon": 'G' },
        # Phase 3 Additions
        { "id": 'evernote', "name": 'Evernote', "category": "Notes", "desc": 'Save notes to your Evernote notebook.', "bg": 'bg-green-50', "text": 'text-green-600', "icon": 'E' },
        { "id": 'linear', "name": 'Linear', "category": "Tasks", "desc": 'Create Linear issues from bugs/tasks.', "bg": 'bg-indigo-50', "text": 'text-indigo-600', "icon": 'Li' },
        { "id": 'jira', "name": 'Jira', "category": "Tasks", "desc": 'Sync tickets and issues.', "bg": 'bg-blue-100', "text": 'text-blue-700', "icon": 'J' },
        { "id": 'clickup', "name": 'ClickUp', "category": "Tasks", "desc": 'Create tasks in ClickUp lists.', "bg": 'bg-purple-50', "text": 'text-purple-600', "icon": 'C' },
        { "id": 'google_drive', "name": 'Google Drive', "category": "Storage", "desc": 'Auto-save audio files to Drive.', "bg": 'bg-green-50', "text": 'text-green-600', "icon": 'GD' },
        { "id": 'dropbox', "name": 'Dropbox', "category": "Storage", "desc": 'Backup recordings to Dropbox.', "bg": 'bg-blue-50', "text": 'text-blue-500', "icon": 'D' },
        { "id": 'email', "name": 'Email (Gmail/Outlook)', "category": "Communication", "desc": 'Email summaries to yourself/team.', "bg": 'bg-slate-100', "text": 'text-slate-600', "icon": '@' },
        { "id": 'bear', "name": 'Bear', "category": "Notes", "desc": 'Export to Bear notes.', "bg": 'bg-red-50', "text": 'text-red-500', "icon": 'B' },
        { "id": 'obsidian', "name": 'Obsidian', "category": "Notes", "desc": 'Sync with Obsidian vault.', "bg": 'bg-fuchsia-50', "text": 'text-fuchsia-600', "icon": 'O' },
        { "id": 'yandex_disk', "name": 'Yandex Disk', "category": "Storage", "desc": 'Upload notes to Yandex.Disk.', "bg": 'bg-red-50', "text": 'text-red-600', "icon": 'Y' },
        { "id": 'weeek', "name": 'WEEEK', "category": "Tasks", "desc": 'Create tasks in WEEEK.', "bg": 'bg-blue-100', "text": 'text-blue-600', "icon": 'W' },
        { "id": 'bitrix24', "name": 'Bitrix24', "category": "Tasks", "desc": 'Create Leads or Tasks via Webhook.', "bg": 'bg-cyan-100', "text": 'text-cyan-600', "icon": 'B24' },
        { "id": 'amocrm', "name": 'AmoCRM', "category": "Tasks", "desc": 'Auto-create Leads from conversations.', "bg": 'bg-blue-500', "text": 'text-white', "icon": 'AMO' },
        { "id": 'kaiten', "name": 'Kaiten', "category": "Tasks", "desc": 'Create cards in Kaiten.', "bg": 'bg-yellow-100', "text": 'text-yellow-700', "icon": 'K' },
        { "id": 'vk', "name": 'VKontakte', "category": "Communication", "desc": 'Publish notes to your VK Wall.', "bg": 'bg-blue-600', "text": 'text-white', "icon": 'VK' },
    ]

@router.post("", response_model=IntegrationResponse)
async def create_or_update_integration(
    integration_data: IntegrationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if exists
    result = await db.execute(
        select(Integration).where(
            Integration.user_id == current_user.id,
            Integration.provider == integration_data.provider
        )
    )
    existing = result.scalars().first()
    
    if existing:
        existing.settings = integration_data.credentials # Using 'settings' column as 'credentials' was schema drift
        await db.commit()
        await db.refresh(existing)
        return {
            "id": existing.id,
            "provider": existing.provider,
            "created_at": existing.created_at,
            "is_active": True,
            "masked_settings": mask_settings(existing.settings)
        }
    else:
        new_int = Integration(
            user_id=current_user.id,
            provider=integration_data.provider,
            settings=integration_data.credentials,
            access_token="mock_token" # Required by model
        )
        db.add(new_int)
        await db.commit()
        await db.refresh(new_int)
        return {
            "id": new_int.id,
            "provider": new_int.provider,
            "created_at": new_int.created_at,
            "is_active": True,
            "masked_settings": mask_settings(new_int.settings)
        }

@router.delete("/{provider}", status_code=204)
async def delete_integration(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Integration).where(
            Integration.user_id == current_user.id,
            Integration.provider == provider
        )
    )
    integration = result.scalars().first()
    if integration:
        await db.delete(integration)
        await db.commit()
    return None

# --- OAuth Flow for Integrations ---

# Shared Config
INTEGRATION_CONFIG = {
    "google_calendar": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scope": "https://www.googleapis.com/auth/calendar.events",
    },
    "google_drive": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scope": "https://www.googleapis.com/auth/drive.file",
    },
    "slack": {
        "auth_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "scope": "chat:write",
    },
    "notion": {
        "auth_url": "https://api.notion.com/v1/oauth/authorize",
        "token_url": "https://api.notion.com/v1/oauth/token",
        "scope": "",
    },
    "yandex_disk": {
        "auth_url": "https://oauth.yandex.ru/authorize",
        "token_url": "https://oauth.yandex.ru/token",
        "scope": "", # Scopes are defined in Yandex App Console
    },
    "amocrm": {
        "auth_url": "https://www.amocrm.ru/oauth", 
        "token_url": "dynamic", 
        "scope": "",
    },
    "vk": {
        "auth_url": "https://oauth.vk.com/authorize",
        "token_url": "https://oauth.vk.com/access_token",
        "scope": "wall,offline",
    }
}

@router.get("/{provider}/auth-url")
async def get_auth_url(provider: str):
    """
    Returns the real OAuth2 URL for the given provider.
    """
    import urllib.parse
    from infrastructure.config import settings

    cfg = INTEGRATION_CONFIG.get(provider)
    if not cfg:
        # Fallback for unlisted (or generic)
        if provider not in ["todoist", "dropbox", "linear", "jira", "clickup"]:
             return {"url": f"{settings.API_BASE_URL}/settings?error=unsupported_provider"}
        
        # Temporary known URLs for others
        base_url = "https://example.com/auth"
        scope = ""
        if provider == "todoist": base_url = "https://todoist.com/oauth/authorize"; scope = "task:add"
        if provider == "linear": base_url = "https://linear.app/oauth/authorize"; scope = "write"
    else:
        base_url = cfg["auth_url"]
        scope = cfg["scope"]
        
    # Get client_id dynamically from settings
    # E.g. provider="google" -> settings.GOOGLE_CLIENT_ID (but here provider is "google_calendar"...)
    # We need a robust mapping or logic.
    # The original code was: os.getenv(f"{provider.upper()}_CLIENT_ID")
    # We can replicate "getattr(settings, ...)"
    
    attr_name = f"{provider.upper()}_CLIENT_ID"
    client_id = getattr(settings, attr_name, None)
    
    # Frontend Callback Route
    redirect_uri = f"{settings.VITE_APP_URL}/settings/callback/{provider}"
    
    if not client_id:
        return {"url": f"{redirect_uri}?code=mock_{provider}_code&state=mock"}

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "access_type": "offline",
        "state": f"{provider}_secure",
        "scope": scope
    }
    
    if provider in ["google_calendar", "google_drive"]:
        params["prompt"] = "consent"

    url_parts = list(urllib.parse.urlparse(base_url))
    url_parts[4] = urllib.parse.urlencode(params)
    return {"url": urllib.parse.urlunparse(url_parts)}


from pydantic import BaseModel
import httpx
import base64

class CallbackRequest(BaseModel):
    provider: str
    code: str
    referer: Optional[str] = None # For AmoCRM

async def exchange_oauth_code(provider: str, code: str, referer: Optional[str] = None) -> dict:
    from infrastructure.config import settings
    
    cfg = INTEGRATION_CONFIG.get(provider)
    if not cfg:
        # Fallback support if we added provider to dict above dynamically
        raise ValueError(f"Provider {provider} not configured for exchange.")

    client_id = getattr(settings, f"{provider.upper()}_CLIENT_ID", None)
    client_secret = getattr(settings, f"{provider.upper()}_CLIENT_SECRET", None)
    redirect_uri = f"{settings.VITE_APP_URL}/settings/callback/{provider}"

    if not client_id or not client_secret:
         raise ValueError("Missing provider credentials.")

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    
    headers = {"Accept": "application/json"}
    
    # Provider specifics
    if provider == "notion":
        auth_str = f"{client_id}:{client_secret}"
        headers["Authorization"] = f"Basic {base64.b64encode(auth_str.encode()).decode()}"
        del payload["client_id"]
        del payload["client_secret"]

    if provider == "amocrm":
        if not referer:
             # Try to guess or fail? Fail.
             # Actually, if referer is missing, we might use default if user set it in env, but referer is safer.
             raise ValueError("Referer (subdomain) required for AmoCRM.")
        token_url = f"https://{referer}/oauth2/access_token"
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data=payload, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"OAuth Exchange Failed: {resp.text}")
        
        data = resp.json()
        if provider == "amocrm":
             data["base_url"] = f"https://{referer}"
        
        return data

@router.post("/callback")
async def integration_callback(
    data: CallbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange code for token and save integration.
    """
    settings_data = {}
    from app.core.security import encrypt_token
    
    # 1. Exchange Code
    if data.code.startswith("mock_"):
        token_data = {
            "access_token": f"mock_access_{data.provider}",
            "refresh_token": f"mock_refresh_{data.provider}",
            "expires_in": 3600
        }
        workspace_name = f"Mock {data.provider.capitalize()}"
    else:
        try:
             token_data = await exchange_oauth_code(data.provider, data.code, data.referer)
        except ValueError as e:
             raise HTTPException(status_code=500, detail=str(e))
             
        workspace_name = f"Connected {data.provider}"
        if "team" in token_data and isinstance(token_data["team"], dict):
            workspace_name = token_data["team"].get("name", workspace_name)

    # 2. Save Integration
    result = await db.execute(
        select(Integration).where(
            Integration.user_id == current_user.id,
            Integration.provider == data.provider
        )
    )
    existing = result.scalars().first()
    
    from datetime import datetime, timedelta, timezone
    expires_in = token_data.get("expires_in")
    expires_at = None
    if expires_in:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        
    settings_data["workspace_name"] = workspace_name
    
    if existing:
        existing.access_token = token_data.get("access_token")
        if token_data.get("refresh_token"):
            existing.refresh_token = token_data.get("refresh_token")
        
        # Add Encrypted Tokens
        existing.encrypted_access_token = encrypt_token(token_data.get("access_token"))
        if token_data.get("refresh_token"):
            existing.encrypted_refresh_token = encrypt_token(token_data.get("refresh_token"))

        existing.expires_at = expires_at
        existing.settings = settings_data
    else:
        new_int = Integration(
            user_id=current_user.id,
            provider=data.provider,
            access_token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            encrypted_access_token=encrypt_token(token_data.get("access_token")),
            encrypted_refresh_token=encrypt_token(token_data.get("refresh_token")),
            expires_at=expires_at,
            settings=settings_data
        )
        db.add(new_int)
    
    await db.commit()
    return {"status": "connected", "provider": data.provider}

class KaitenAuth(BaseModel):
    api_key: str

@router.post("/kaiten/boards")
async def fetch_kaiten_boards(auth: KaitenAuth):
    """
    Fetch available boards from Kaiten.
    """
    # Assuming standard cloud Kaiten or customized via env? 
    # User requirement doesn't specify on-prem.
    url = "https://kaiten.ru/api/latest/boards"
    headers = {
        "Authorization": f"Bearer {auth.api_key}",
        "Accept": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
             raise HTTPException(status_code=400, detail=f"Failed to fetch boards: {resp.text}")
        
        return resp.json()
@router.post("/google-maps/connect")
async def connect_google_maps(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """Initiate Google Maps connection via OAuth code."""
    from app.services.integrations.google_maps_service import google_maps_service
    status = await google_maps_service.connect(current_user.id, code)
    return {"status": status}

@router.post("/google-maps/callback")
async def google_maps_callback(
    code: str,
    state: str,
    current_user: User = Depends(get_current_user)
):
    """Callback for Google Maps OAuth."""
    from app.services.integrations.google_maps_service import google_maps_service
    status = await google_maps_service.connect(current_user.id, code)
    return {"status": status}
@router.post("/yandex-maps/connect")
async def connect_yandex_maps(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """Initiate Yandex Maps connection via OAuth code."""
    from app.services.integrations.yandex_maps_service import yandex_maps_service
    status = await yandex_maps_service.connect(current_user.id, code)
    return {"status": status}

@router.post("/yandex-maps/callback")
async def yandex_maps_callback(
    code: str,
    state: str = None,
    current_user: User = Depends(get_current_user)
):
    """Callback for Yandex Maps OAuth."""
    from app.services.integrations.yandex_maps_service import yandex_maps_service
    status = await yandex_maps_service.connect(current_user.id, code)
    return {"status": status}
@router.post("/apple-reminders/connect")
async def connect_apple_reminders(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """Connect Apple Reminders."""
    from app.services.integrations.tasks_service import tasks_service
    status = await tasks_service.connect_apple(current_user.id, code)
    return {"status": status}

@router.post("/google-tasks/connect")
async def connect_google_tasks(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """Connect Google Tasks."""
    from app.services.integrations.tasks_service import tasks_service
    status = await tasks_service.connect_google_tasks(current_user.id, code)
    return {"status": status}

@router.post("/google-tasks/callback")
async def google_tasks_callback(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """Callback for Google Tasks."""
    from app.services.integrations.tasks_service import tasks_service
    status = await tasks_service.connect_google_tasks(current_user.id, code)
    return {"status": status}

@router.post("/gmail/connect")
async def connect_gmail(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """Connect Gmail."""
    from app.services.integrations.email_service import email_service
    status = await email_service.connect_gmail(current_user.id, code)
    return {"status": status}

@router.post("/gmail/callback")
async def gmail_callback(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """Callback for Gmail."""
    from app.services.integrations.email_service import email_service
    await email_service.connect_gmail(current_user.id, code)
    return {"status": "Connected"}

@router.post("/outlook/connect")
async def connect_outlook(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """Connect Outlook."""
    from app.services.integrations.email_service import email_service
    status = await email_service.connect_outlook(current_user.id, code)
    return {"status": status}

@router.post("/outlook/callback")
async def outlook_callback(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """Callback for Outlook."""
    from app.services.integrations.email_service import email_service
    await email_service.connect_outlook(current_user.id, code)
    return {"status": "Connected"}

@router.post("/readwise/connect")
async def connect_readwise(
    token: str,
    current_user: User = Depends(get_current_user)
):
    """Connect Readwise."""
    from app.services.integrations.readwise_service import readwise_service
    status = await readwise_service.connect(current_user.id, token)
    return {"status": status}

@router.post("/obsidian/connect")
async def connect_obsidian(
    vault_path: str,
    current_user: User = Depends(get_current_user)
):
    """Connect Obsidian/Logseq local vault."""
    from app.services.integrations.obsidian_service import obsidian_service
    status = await obsidian_service.connect(current_user.id, vault_path)
    return {"status": status}

@router.post("/yandex-tasks/connect")
async def connect_yandex_tasks(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """Connect Yandex Tasks."""
    from app.services.integrations.yandex_tasks_service import yandex_tasks_service
    status = await yandex_tasks_service.connect(current_user.id, code)
    return {"status": status}

@router.post("/yandex-tasks/callback")
async def yandex_tasks_callback(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """Callback for Yandex Tasks."""
    from app.services.integrations.yandex_tasks_service import yandex_tasks_service
    await yandex_tasks_service.connect(current_user.id, code)
    return {"status": "Connected"}

@router.post("/2gis/connect")
async def connect_2gis(
    token: str,
    current_user: User = Depends(get_current_user)
):
    """Connect 2GIS account."""
    async with AsyncSessionLocal() as db:
        # Simplified storage
        from app.models import Integration
        from sqlalchemy.future import select
        from app.core.security import encrypt_token
        
        result = await db.execute(select(Integration).where(Integration.user_id == current_user.id, Integration.provider == "2gis"))
        it = result.scalars().first()
        if not it:
            it = Integration(user_id=current_user.id, provider="2gis")
            db.add(it)
        it.twogis_token = encrypt_token(token)
        await db.commit()
    return {"status": "Connected to 2GIS"}

@router.post("/mapsme/connect")
async def connect_mapsme(
    path: str,
    current_user: User = Depends(get_current_user)
):
    """Connect Maps.me by providing KML path."""
    async with AsyncSessionLocal() as db:
        from app.models import Integration
        from sqlalchemy.future import select
        from app.core.security import encrypt_token
        
        result = await db.execute(select(Integration).where(Integration.user_id == current_user.id, Integration.provider == "mapsme"))
        it = result.scalars().first()
        if not it:
            it = Integration(user_id=current_user.id, provider="mapsme")
            db.add(it)
        it.mapsme_path = encrypt_token(path)
        await db.commit()
    return {"status": "Connected to Maps.me vault"}
