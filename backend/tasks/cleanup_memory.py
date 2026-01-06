from celery import shared_task
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete
from loguru import logger
import asyncio

from infrastructure.database import AsyncSessionLocal
from app.models import Note, LongTermMemory

async def run_cleanup():
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        
        # 1. Notes: score < 4 AND older than 90 days
        note_cutoff = now - timedelta(days=90)
        note_stmt = delete(Note).where(
            Note.importance_score < 4,
            Note.created_at < note_cutoff
        )
        note_res = await session.execute(note_stmt)
        
        # 2. LongTermMemory: score < 5 AND older than 180 days
        ltm_cutoff = now - timedelta(days=180)
        ltm_stmt = delete(LongTermMemory).where(
            LongTermMemory.importance_score < 5,
            LongTermMemory.created_at < ltm_cutoff
        )
        ltm_res = await session.execute(ltm_stmt)
        
        await session.commit()
        
        logger.info(f"Memory Cleanup: Deleted {note_res.rowcount} low-score notes and {ltm_res.rowcount} long-term memories.")

@shared_task(name="cleanup_memory")
def cleanup_memory():
    """Celery task to perform memory forgetting and cleanup."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # This is for when we run in a context where an event loop is already running
        asyncio.ensure_future(run_cleanup())
    else:
        asyncio.run(run_cleanup())
