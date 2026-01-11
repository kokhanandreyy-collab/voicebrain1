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
    """
    Logic for Soft Forgetting:
    1. Hard Delete: ONLY records older than 365 days.
    2. Soft Archiving: 
       - Records older than 180 days.
       - Records with very low importance (< 3.0) regardless of age (if > 30 days).
    """
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        
        # 1. Hard Delete (Strictly > 365 days)
        hard_cutoff = now - timedelta(days=365)
        hard_stmt = delete(LongTermMemory).where(LongTermMemory.created_at < hard_cutoff)
        hard_res = await session.execute(hard_stmt)
        hard_count = hard_res.rowcount
        
        # 2. Soft Archive (Soft Forgetting)
        # Conditions: (age > 180 days) OR (score < 3.0 AND age > 30 days)
        soft_cutoff_age = now - timedelta(days=180)
        soft_cutoff_low_score = now - timedelta(days=30)
        
        soft_query = select(LongTermMemory).where(
            LongTermMemory.is_archived == False,
            (LongTermMemory.created_at < soft_cutoff_age) | 
            ((LongTermMemory.importance_score < 3.0) & (LongTermMemory.created_at < soft_cutoff_low_score))
        )
        soft_targets_res = await session.execute(soft_query)
        soft_targets = soft_targets_res.scalars().all()
        
        archived_count = 0
        for mem in soft_targets:
            # Compression: generate ultra-summary before archiving
            mem.archived_summary = await generate_ultra_summary(mem.summary_text)
            mem.is_archived = True
            archived_count += 1
            
            
        # 3. Notes cleanup (Standard deletion for medium-term storage)
        note_cutoff = now - timedelta(days=90)
        note_stmt = delete(Note).where(
            Note.importance_score < 4,
            Note.created_at < note_cutoff
        )
        note_res = await session.execute(note_stmt)
        
        # 4. Graph Cleanup (Requirement: TTL 180 days, Weak relations)
        # Delete relations older than 180 days
        rel_ttl_cutoff = now - timedelta(days=180)
        rel_ttl_stmt = delete(NoteRelation).where(NoteRelation.created_at < rel_ttl_cutoff)
        rel_ttl_res = await session.execute(rel_ttl_stmt)

        # Delete weak relations (strength < 0.5) if older than 30 days
        rel_weak_cutoff = now - timedelta(days=30)
        rel_weak_stmt = delete(NoteRelation).where(
            NoteRelation.strength < 0.5,
            NoteRelation.created_at < rel_weak_cutoff
        )
        rel_weak_res = await session.execute(rel_weak_stmt)

        # 5. Enforce Max Degree (10) - Opportunistic Cleanup
        # Find nodes with > 10 relations
        # This is expensive to do for all, so we can pick a strategy or do nothing here as 
        # insertion logic (in reflection) already checks it.
        # But let's delete lowest strength if > 10.
        # (Omitted here for performance, relying on insertion checks)
        
        await session.commit()
        
        # Monitoring
        total_notes = (await session.execute(select(func.count(Note.id)))).scalar()
        total_rels = (await session.execute(select(func.count(NoteRelation.id)))).scalar()
        monitor.update_graph_metrics(total_notes, total_rels)
        
        logger.info(
            f"Cleanup: Hard {hard_count}, Arch {archived_count}, Notes {note_res.rowcount}, "
            f"RelTTL {rel_ttl_res.rowcount}, RelWeak {rel_weak_res.rowcount}"
        )
        return hard_count, archived_count

@shared_task(name="cleanup_memory")
def cleanup_memory():
    """Celery task entry point."""
    return async_to_sync(run_cleanup)()
