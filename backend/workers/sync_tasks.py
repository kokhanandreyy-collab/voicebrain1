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

        if integration.provider in ["gmail", "outlook"]:
            sync_email.delay(note.id, integration.provider)
            continue

        if integration.provider == "readwise":
            sync_readwise.delay(note.id)
            continue

        if integration.provider == "obsidian":
            sync_obsidian.delay(note.id)
            continue

        if integration.provider == "yandex_tasks":
            sync_yandex_tasks.delay(note.id)
            continue

        if integration.provider in ["2gis", "mapsme"]:
            sync_maps.delay(note.id, integration.provider)
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
    from app.services.pipeline import pipeline
    await pipeline.process(note_id)

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

async def _sync_email_async(note_id: str, provider: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Note).where(Note.id == note_id))
        note = result.scalars().first()
        if not note: return
        
        from app.services.integrations.email_service import email_service
        await email_service.create_or_update_draft(note.user_id, note.id, note.transcription_text, provider=provider)

@celery.task(name="sync.email")
def sync_email(note_id: str, provider: str):
    async_to_sync(_sync_email_async)(note_id, provider)
    return {"status": "synced_email", "provider": provider, "note_id": note_id}

async def _sync_readwise_async(note_id: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Note).where(Note.id == note_id))
        note = result.scalars().first()
        if not note: return
        
        from app.services.integrations.readwise_service import readwise_service
        await readwise_service.create_or_update_highlight(note.user_id, note.id, note.transcription_text)

@celery.task(name="sync.readwise")
def sync_readwise(note_id: str):
    async_to_sync(_sync_readwise_async)(note_id)
    return {"status": "synced_readwise", "note_id": note_id}

async def _sync_obsidian_async(note_id: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Note).where(Note.id == note_id))
        note = result.scalars().first()
        if not note: return
        
        from app.services.integrations.obsidian_service import obsidian_service
        await obsidian_service.create_or_update_note(note.user_id, note.id, note.transcription_text)

@celery.task(name="sync.obsidian")
def sync_obsidian(note_id: str):
    async_to_sync(_sync_obsidian_async)(note_id)
    return {"status": "synced_obsidian", "note_id": note_id}

async def _sync_yandex_tasks_async(note_id: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Note).where(Note.id == note_id))
        note = result.scalars().first()
        if not note: return
        
        from app.services.integrations.yandex_tasks_service import yandex_tasks_service
        await yandex_tasks_service.create_or_update_task(note.user_id, note.id, note.transcription_text)

@celery.task(name="sync.yandex_tasks")
def sync_yandex_tasks(note_id: str):
    async_to_sync(_sync_yandex_tasks_async)(note_id)
    return {"status": "synced_yandex_tasks", "note_id": note_id}

async def _sync_maps_async(note_id: str, provider: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Note).where(Note.id == note_id))
        note = result.scalars().first()
        if not note: return
        
        from app.services.integrations.maps_service import maps_service
        if provider == "2gis":
            await maps_service.create_or_update_place_2gis(note.user_id, note.id, note.transcription_text)
        elif provider == "mapsme":
            await maps_service.create_or_update_place_mapsme(note.user_id, note.id, note.transcription_text)

@celery.task(name="sync.maps")
def sync_maps(note_id: str, provider: str):
    async_to_sync(_sync_maps_async)(note_id, provider)
    return {"status": "synced_maps", "provider": provider, "note_id": note_id}

@celery.task(name="sync.process_note")
def process_sync(note_id: str):
    async_to_sync(_process_sync_async)(note_id)
    return {"status": "synced", "note_id": note_id}
