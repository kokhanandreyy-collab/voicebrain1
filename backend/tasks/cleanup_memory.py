from celery import shared_task
from loguru import logger
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, update, select, func
from asgiref.sync import async_to_sync

from infrastructure.database import AsyncSessionLocal
from app.models import Note, LongTermMemory, NoteRelation
from app.services.ai_service import ai_service
from infrastructure.monitoring import monitor

async def generate_ultra_summary(text: str) -> str:
    """Generate a highly compressed summary (50-100 words)."""
    try:
        prompt = (
            "Compress the following memory into an ultra-short summary (50-100 words) "
            "that captures only the most essential facts for long-term archival.\n\n"
            f"Original Memory:\n{text}"
        )
        summary = await ai_service.get_chat_completion([
            {"role": "system", "content": "You are a memory compression agent. Be concise."},
            {"role": "user", "content": prompt}
        ])
        return summary
    except Exception as e:
        logger.error(f"Failed to generate ultra-summary: {e}")
        return text[:300] # Fallback to truncated text

async def run_cleanup():
    """Logic for soft forgetting, archiving, and hard deletion."""
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        
        # 1. Hard Delete very old (>365 days) OR very low importance (< 2.0)
        hard_cutoff = now - timedelta(days=365)
        hard_stmt = delete(LongTermMemory).where(
            (LongTermMemory.created_at < hard_cutoff) | 
            (LongTermMemory.importance_score < 2.0)
        )
        hard_res = await session.execute(hard_stmt)
        hard_count = hard_res.rowcount
        
        # 2. Soft Archive (score < 5 AND older than 180 days)
        soft_cutoff = now - timedelta(days=180)
        soft_query = select(LongTermMemory).where(
            LongTermMemory.is_archived == False,
            LongTermMemory.importance_score < 5.0,
            LongTermMemory.created_at < soft_cutoff
        )
        soft_targets_res = await session.execute(soft_query)
        soft_targets = soft_targets_res.scalars().all()
        
        archived_count = 0
        for mem in soft_targets:
            # Generate ultra-summary before archiving
            mem.archived_summary = await generate_ultra_summary(mem.summary_text)
            mem.is_archived = True
            archived_count += 1
            
        # 3. Notes cleanup
        note_cutoff = now - timedelta(days=90)
        note_stmt = delete(Note).where(
            Note.importance_score < 4,
            Note.created_at < note_cutoff
        )
        note_res = await session.execute(note_stmt)
        
        await session.commit()
        
        # Monitoring: Graph Size after cleanup
        total_notes = (await session.execute(select(func.count(Note.id)))).scalar()
        total_rels = (await session.execute(select(func.count(NoteRelation.id)))).scalar()
        monitor.update_graph_metrics(total_notes, total_rels)
        
        logger.info(
            f"Memory Cleanup: Hard deleted {hard_count} LTM records, "
            f"Soft archived {archived_count} records, "
            f"Deleted {note_res.rowcount} low-score notes."
        )
        return hard_count, archived_count

@shared_task(name="cleanup_memory")
def cleanup_memory():
    """Celery task entry point."""
    return async_to_sync(run_cleanup)()
