from datetime import datetime, timedelta, timezone
from loguru import logger
from sqlalchemy.future import select
from asgiref.sync import async_to_sync

from app.celery_app import celery
from app.models import Note, LongTermMemory
from infrastructure.database import AsyncSessionLocal
from infrastructure.storage import storage_client

async def _cleanup_memory_async():
    logger.info("Starting memory cleanup (Task)...")
    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)
            cutoff_notes = now - timedelta(days=90)
            cutoff_ltm = now - timedelta(days=180)
            
            # 1. Notes (Score < 4, > 90 days)
            res_notes = await db.execute(select(Note).where(
                Note.importance_score < 4.0,
                Note.created_at < cutoff_notes
            ))
            notes_to_del = res_notes.scalars().all()
            
            c_notes = 0
            for n in notes_to_del:
                if n.storage_key:
                    try: await storage_client.delete_file(n.storage_key)
                    except Exception: pass
                db.delete(n)
                c_notes += 1
            
            # 2. LongTermMemory (Score < 5, > 180 days)
            res_mems = await db.execute(select(LongTermMemory).where(
                LongTermMemory.importance_score < 5.0,
                LongTermMemory.created_at < cutoff_ltm
            ))
            mems_to_del = res_mems.scalars().all()
            
            c_mems = 0
            for m in mems_to_del:
                db.delete(m) # Sync
                c_mems += 1
            
            await db.commit()
            logger.info(f"Memory Cleanup: Deleted {c_notes} Notes, {c_mems} LongTermMemories.")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            print(f"DEBUG EXCEPTION: {e}")
            await db.rollback()

@celery.task(name="cleanup_memory")
def cleanup_memory():
    async_to_sync(_cleanup_memory_async)()
