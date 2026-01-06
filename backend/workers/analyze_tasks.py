from typing import Dict, Any, List, Optional
from loguru import logger
from asgiref.sync import async_to_sync
from sqlalchemy.future import select
import json
import datetime

from app.celery_app import celery
from app.services.ai_service import ai_service
from app.models import Note, User, CachedAnalysis, NoteStatus
from infrastructure.database import AsyncSessionLocal
from infrastructure.metrics import track_cache_hit, track_cache_miss
from app.core.analyze_core import rag_service, analyze_core

async def _process_analyze_async(note_id: str) -> None:
    logger.info(f"Starting analysis for note {note_id} (dynamic)")
    async with AsyncSessionLocal() as db:
        # Business logic fully encapsulated in analyze_core
        # We fetch the note once here to get the user_id for the subsequent task
        res_note = await db.execute(select(Note).where(Note.id == note_id))
        note = res_note.scalars().first()
        if not note: return

        await analyze_core.analyze_note_by_id(note_id, db, short_term_memory)
        
        # Trigger follow-up Reflection (requires user_id)
        from workers.reflection_tasks import reflection_incremental
        reflection_incremental.delay(note.user_id)

@celery.task(name="analyze.process_note", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_analyze(note_id: str):
    async_to_sync(_process_analyze_async)(note_id)
    return {"status": "completed", "note_id": note_id}
