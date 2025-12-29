import inspect
import json
from typing import List, Optional, Dict, Any
from loguru import logger
from asgiref.sync import async_to_sync
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.celery_app import celery
from app.models import Note, Integration, User, IntegrationLog
from app.core.database import AsyncSessionLocal
from app.services.integrations import get_integration_handler
from app.core.config import settings
from common.utils import escape_markdown

async def step_sync_integrations(note: Note, db) -> None:
    ai_analysis_data = note.ai_analysis or {}
    explicit_app = ai_analysis_data.get("explicit_destination_app")
    
    int_result = await db.execute(select(Integration).where(
        Integration.user_id == note.user_id
    ).options(selectinload(Integration.user)))
    user_integrations = list(int_result.scalars().all())

    if explicit_app:
        user_integrations = [i for i in user_integrations if i.provider == explicit_app]

    for integration in user_integrations:
        if integration.provider == "google_maps":
            sync_google_maps.delay(note.id)
            continue
        
        if integration.provider == "yandex_maps":
            sync_yandex_maps.delay(note.id)
            continue

        if integration.provider in ["apple_reminders", "google_tasks"]:
            sync_tasks.delay(note.id, integration.provider)
            continue
            
        handler = get_integration_handler(integration.provider)
        if handler:
            status, error = "SUCCESS", None
            try:
                sig = inspect.signature(handler.sync)
                if 'db' in sig.parameters:
                    await handler.sync(integration, note, db=db)
                else:
                    await handler.sync(integration, note)
            except Exception as int_err:
                logger.error(f"Sync failed for {integration.provider}: {int_err}")
                status, error = "FAILED", str(int_err)
            
            db.add(IntegrationLog(integration_id=integration.id, note_id=note.id, status=status, error_message=error))

async def _process_sync_async(note_id: str) -> None:
    logger.info(f"[Sync] Processing note: {note_id}")
    db = AsyncSessionLocal()
    try:
        result = await db.execute(select(Note).where(Note.id == note_id))
        note = result.scalars().first()
        if not note: return

        await step_sync_integrations(note, db)
        
        note.status = "COMPLETED"
        note.processing_step = "Completed"
        await db.commit()

        # Notifications
        user_res = await db.execute(select(User).where(User.id == note.user_id))
        user = user_res.scalars().first()
        if user:
            # Telegram
            if user.telegram_chat_id:
                from app.core.bot import bot
                if bot:
                    try:
                        safe_title = escape_markdown(note.title or "Untitled")
                        safe_intent = escape_markdown((note.ai_analysis or {}).get("intent", "note"))
                        msg = f"✅ **Saved!**\nTitle: {safe_title}\nIntent: {safe_intent}"
                        await bot.send_message(chat_id=user.telegram_chat_id, text=msg, parse_mode="Markdown")
                    except Exception as e: logger.warning(f"TG notify failed: {e}")

            # Push
            if user.push_subscriptions and settings.VAPID_PRIVATE_KEY:
                from pywebpush import webpush
                payload = json.dumps({"title": "Note Processed", "body": f"{note.title} analyzed.", "url": f"/dashboard?note={note.id}"})
                for sub in user.push_subscriptions:
                    try:
                        webpush(subscription_info=sub, data=payload, vapid_private_key=settings.VAPID_PRIVATE_KEY, vapid_claims={"sub": settings.VAPID_CLAIMS_EMAIL})
                    except Exception: pass

    except Exception as e:
        logger.error(f"Sync task failed: {e}")
        from workers.common_tasks import handle_note_failure
        await handle_note_failure(note_id, str(e))
    finally:
        await db.close()

async def _sync_google_maps_async(note_id: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Note).where(Note.id == note_id))
        note = result.scalars().first()
        if not note: return
        
        from app.services.integrations.google_maps_service import google_maps_service
        await google_maps_service.create_or_update_place(note.user_id, note.id, note.transcription_text)

@celery.task(name="sync.google_maps")
def sync_google_maps(note_id: str):
    async_to_sync(_sync_google_maps_async)(note_id)
    return {"status": "synced_google_maps", "note_id": note_id}

async def _sync_yandex_maps_async(note_id: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Note).where(Note.id == note_id))
        note = result.scalars().first()
        if not note: return
        
        from app.services.integrations.yandex_maps_service import yandex_maps_service
        await yandex_maps_service.create_or_update_place(note.user_id, note.id, note.transcription_text)

@celery.task(name="sync.yandex_maps")
def sync_yandex_maps(note_id: str):
    async_to_sync(_sync_yandex_maps_async)(note_id)
    return {"status": "synced_yandex_maps", "note_id": note_id}

async def _sync_tasks_async(note_id: str, provider: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Note).where(Note.id == note_id))
        note = result.scalars().first()
        if not note: return
        
        from app.services.integrations.tasks_service import tasks_service
        await tasks_service.create_or_update_reminder(note.user_id, note.id, note.transcription_text, provider=provider)

@celery.task(name="sync.tasks")
def sync_tasks(note_id: str, provider: str):
    async_to_sync(_sync_tasks_async)(note_id, provider)
    return {"status": "synced_tasks", "provider": provider, "note_id": note_id}

@celery.task(name="sync.process_note")
def process_sync(note_id: str):
    async_to_sync(_process_sync_async)(note_id)
    return {"status": "synced", "note_id": note_id}
