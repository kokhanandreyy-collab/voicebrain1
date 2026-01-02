from typing import List
from loguru import logger
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import inspect

from app.models import Note, Integration, IntegrationLog
from app.services.integrations import get_integration_handler

# For firing specific sub-tasks to workers if strictly needed (e.g. rate limits),
# but here we implement the logic directly or call workers?
# The request said "Move business logic ... to core/".
# Workers should be just wrappers.
# So `sync_service` should contain the logic `step_sync_integrations`.
# But `step_sync_integrations` invoked `sync_tasks.delay`.
# If `sync_tasks` are just wrappers, they must call `sync_service.sync_one(provider)`.
# This creates a loop: sync_service -> sync_tasks (celery) -> sync_service.
# This is fine for Async execution.
# So `sync_service.sync_note` iterates integrations and calls Celery tasks.
# And `Celery task` calls `sync_service.perform_sync(note_id, provider)`.

class SyncService:
    async def sync_note(self, note: Note, db: AsyncSession):
        """Dispatches sync tasks for all active integrations."""
        ai_analysis_data = note.ai_analysis or {}
        explicit_app = ai_analysis_data.get("explicit_destination_app")
        
        int_result = await db.execute(select(Integration).where(
            Integration.user_id == note.user_id
        ).options(selectinload(Integration.user)))
        user_integrations = list(int_result.scalars().all())

        if explicit_app:
            user_integrations = [i for i in user_integrations if i.provider == explicit_app]

        # Import celery tasks here to avoid circular imports at top level if necessary
        from workers.sync_tasks import (
            sync_google_maps, sync_yandex_maps, sync_tasks, sync_email,
            sync_readwise, sync_obsidian, sync_yandex_tasks, sync_maps
        )

        for integration in user_integrations:
            if integration.provider == "google_maps":
                sync_google_maps.delay(note.id)
            elif integration.provider == "yandex_maps":
                sync_yandex_maps.delay(note.id)
            elif integration.provider in ["apple_reminders", "google_tasks"]:
                sync_tasks.delay(note.id, integration.provider)
            elif integration.provider in ["gmail", "outlook"]:
                sync_email.delay(note.id, integration.provider)
            elif integration.provider == "readwise":
                sync_readwise.delay(note.id)
            elif integration.provider == "obsidian":
                sync_obsidian.delay(note.id)
            elif integration.provider == "yandex_tasks":
                sync_yandex_tasks.delay(note.id)
            elif integration.provider in ["2gis", "mapsme"]:
                sync_maps.delay(note.id, integration.provider)
            else:
                # Direct sync or generic handler?
                pass
                
    async def perform_sync(self, note_id: str, provider: str, db: AsyncSession):
        """Actual sync logic for a single integration."""
        result = await db.execute(select(Note).where(Note.id == note_id))
        note = result.scalars().first()
        if not note: return

        # Fetch integration again to be sure
        int_result = await db.execute(select(Integration).where(
            Integration.user_id == note.user_id,
            Integration.provider == provider
        ))
        integration = int_result.scalars().first()
        if not integration: return

        handler = get_integration_handler(provider)
        status, error = "SUCCESS", None
        
        if handler:
            try:
                sig = inspect.signature(handler.sync)
                if 'db' in sig.parameters:
                    await handler.sync(integration, note, db=db)
                else:
                    await handler.sync(integration, note)
            except Exception as e:
                logger.error(f"Sync failed for {provider}: {e}")
                status, error = "FAILED", str(e)
        
        db.add(IntegrationLog(integration_id=integration.id, note_id=note.id, status=status, error_message=error))
        await db.commit()
    
    # Specific specialized methods can be added if needed, 
    # but `perform_sync` with `get_integration_handler` covers most.
    # The map services had separate methods in `sync_tasks.py` because they aren't fully unified in `services/integrations`?
    # Let's check `sync_tasks.py`. `sync_google_maps` called `google_maps_service`.
    # `perform_sync` uses `get_integration_handler`.
    # If `google_maps` has a handler in `services/integrations/__init__.py`, `perform_sync` works.
    # If not, we need explicit methods.
    
    async def perform_sync_maps(self, note_id: str, provider: str, db: AsyncSession):
        # ... logic from sync_tasks ...
        result = await db.execute(select(Note).where(Note.id == note_id))
        note = result.scalars().first()
        if not note: return

        if provider == "google_maps":
            from app.services.integrations.google_maps_service import google_maps_service
            await google_maps_service.create_or_update_place(note.user_id, note.id, note.transcription_text)
        elif provider == "yandex_maps":
            from app.services.integrations.yandex_maps_service import yandex_maps_service
            await yandex_maps_service.create_or_update_place(note.user_id, note.id, note.transcription_text)
        elif provider in ["2gis", "mapsme"]:
            from app.services.integrations.maps_service import maps_service
            if provider == "2gis":
                await maps_service.create_or_update_place_2gis(note.user_id, note.id, note.transcription_text)
            elif provider == "mapsme":
                await maps_service.create_or_update_place_mapsme(note.user_id, note.id, note.transcription_text)

    async def perform_sync_tasks(self, note_id: str, provider: str, db: AsyncSession):
         result = await db.execute(select(Note).where(Note.id == note_id))
         note = result.scalars().first()
         if not note: return
         
         from app.services.integrations.tasks_service import tasks_service
         await tasks_service.create_or_update_reminder(note.user_id, note.id, note.transcription_text, provider=provider)

    async def perform_sync_email(self, note_id: str, provider: str, db: AsyncSession):
         result = await db.execute(select(Note).where(Note.id == note_id))
         note = result.scalars().first()
         if not note: return
         from app.services.integrations.email_service import email_service
         await email_service.create_or_update_draft(note.user_id, note.id, note.transcription_text, provider=provider)
    
    async def perform_sync_readwise(self, note_id: str, db: AsyncSession):
         result = await db.execute(select(Note).where(Note.id == note_id))
         note = result.scalars().first()
         if not note: return
         from app.services.integrations.readwise_service import readwise_service
         await readwise_service.create_or_update_highlight(note.user_id, note.id, note.transcription_text)

    async def perform_sync_obsidian(self, note_id: str, db: AsyncSession):
         result = await db.execute(select(Note).where(Note.id == note_id))
         note = result.scalars().first()
         if not note: return
         from app.services.integrations.obsidian_service import obsidian_service
         await obsidian_service.create_or_update_note(note.user_id, note.id, note.transcription_text)
    
    async def perform_sync_yandex_tasks(self, note_id: str, db: AsyncSession):
         result = await db.execute(select(Note).where(Note.id == note_id))
         note = result.scalars().first()
         if not note: return
         from app.services.integrations.yandex_tasks_service import yandex_tasks_service
         await yandex_tasks_service.create_or_update_task(note.user_id, note.id, note.transcription_text)

sync_service = SyncService()
