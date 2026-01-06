from typing import Dict, Any, List, Optional
from loguru import logger
from asgiref.sync import async_to_sync
from sqlalchemy.future import select
from sqlalchemy import update
import json
import datetime

from app.celery_app import celery
from app.services.ai_service import ai_service
from app.models import Note, User, CachedAnalysis, NoteStatus
from infrastructure.database import AsyncSessionLocal
from infrastructure.metrics import track_cache_hit, track_cache_miss
from app.core.analyze_core import rag_service, analyze_core
from infrastructure.redis_client import short_term_memory

async def _process_analyze_async(note_id: str) -> None:
    logger.info(f"Starting dynamic analysis for note {note_id}")
    async with AsyncSessionLocal() as db:
        # 1. Fetch State
        res_note = await db.execute(select(Note).where(Note.id == note_id))
        note = res_note.scalars().first()
        if not note or not note.transcription_text:
            return

        res_user = await db.execute(select(User).where(User.id == note.user_id))
        user = res_user.scalars().first()
        
        # 2. Semantic Cache Check
        current_embedding = await ai_service.generate_embedding(note.transcription_text)
        cache_hit = False
        analysis = None

        try:
            cache_res = await db.execute(
                select(CachedAnalysis)
                .where(
                    CachedAnalysis.user_id == note.user_id,
                    CachedAnalysis.embedding.cosine_distance(current_embedding) < 0.1,
                    CachedAnalysis.expires_at > datetime.datetime.now(datetime.timezone.utc)
                )
                .order_by(CachedAnalysis.embedding.cosine_distance(current_embedding))
                .limit(1)
            )
            cached_entry = cache_res.scalars().first()
            if cached_entry:
                logger.info(f"Cache hit: используя этот результат для {note_id}")
                track_cache_hit("note_analysis")
                analysis = cached_entry.result
                cache_hit = True
        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}")

        if not cache_hit:
            track_cache_miss("note_analysis")
            # 3. Build Dynamic Prompt
            ctx_parts = []
            if user:
                if user.identity_summary:
                    ctx_parts.append(f"User identity: {user.identity_summary}")
                if user.adaptive_preferences:
                    prefs_json = json.dumps(user.adaptive_preferences)
                    ctx_parts.append(f"Adaptive preferences: {prefs_json}")
                
                # Long-term knowledge from RAG
                lt_summaries = await rag_service.get_long_term_memory(user.id, db)
                if lt_summaries and "No long-term" not in lt_summaries:
                    ctx_parts.append(f"Long-term knowledge: {lt_summaries}")

            dynamic_context = "\n".join(ctx_parts)
            
            # 4. Call AI
            analysis = await ai_service.analyze_text(
                note.transcription_text,
                user_context=dynamic_context,
                target_language=user.target_language if user else "Original"
            )
            
            # Save to Cache
            try:
                ttl = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
                db.add(CachedAnalysis(
                    user_id=note.user_id,
                    embedding=current_embedding,
                    result=analysis,
                    expires_at=ttl
                ))
            except Exception as e:
                logger.warning(f"Cache save failed: {e}")

        # 5. Apply & Save
        analyze_core._apply_analysis_to_note(note, analysis)
        note.status = NoteStatus.ANALYZED
        await db.commit()
        
        # Trigger follow-up services (Reflection, etc.)
        from workers.reflection_tasks import reflection_incremental
        reflection_incremental.delay(note.user_id)

@celery.task(name="analyze.process_note", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_analyze(note_id: str):
    async_to_sync(_process_analyze_async)(note_id)
    return {"status": "completed", "note_id": note_id}
