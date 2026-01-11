from celery import shared_task
from loguru import logger
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete
from asgiref.sync import async_to_sync

from infrastructure.database import AsyncSessionLocal
from app.models import Note, LongTermMemory

async def run_cleanup():
    """Logic to delete low-importance old memories."""
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        
        # 1. Delete from Note where importance_score < 4 and created_at < (now - 90 days)
        note_cutoff = now - timedelta(days=90)
        note_stmt = delete(Note).where(
            Note.importance_score < 4,
            Note.created_at < note_cutoff
        )
        note_res = await session.execute(note_stmt)
        
        # 2. Delete from LongTermMemory where importance_score < 5 and created_at < (now - 180 days)
        ltm_cutoff = now - timedelta(days=180)
        ltm_stmt = delete(LongTermMemory).where(
            LongTermMemory.importance_score < 5,
            LongTermMemory.created_at < ltm_cutoff
        )
        ltm_res = await session.execute(ltm_stmt)
        
        await session.commit()
        
        deleted_notes = note_res.rowcount
        deleted_ltm = ltm_res.rowcount
        
        logger.info(f"Cleanup complete: Deleted {deleted_notes} notes and {deleted_ltm} long-term records.")
        return deleted_notes, deleted_ltm

@shared_task(name="cleanup_memory")
def cleanup_memory():
    """Celery task entry point."""
    return async_to_sync(run_cleanup)()
