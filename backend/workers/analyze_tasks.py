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
        cached_entry = None

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
        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}")

        if cached_entry:
            analysis = cached_entry.result
            dynamic_prompt = f"Используй этот cached result: {json.dumps(analysis, ensure_ascii=False)}"
            logger.info(f"Cache hit: {dynamic_prompt}")
            track_cache_hit("note_analysis")
            cache_hit = True
        else:
            track_cache_miss("note_analysis")
            # 3. Build Dynamic Prompt with Memory (Miss case)
            ctx_parts = []
            lt_summaries = ""
            recent_notes = []
            
            if user:
                # 3.1 Always include Identity
                if user.identity_summary:
                    ctx_parts.append(f"User identity: {user.identity_summary}")
                
                if user.adaptive_preferences:
                    ctx_parts.append(f"Adaptive preferences: {json.dumps(user.adaptive_preferences, ensure_ascii=False)}")
                
                # 3.2 Fetch Memories
                # Long-term (Top-3 already limited in rag_service)
                lt_summaries = await rag_service.get_long_term_memory(user.id, db)
                if lt_summaries and "No long-term" not in lt_summaries:
                    ctx_parts.append(f"Long-term knowledge: {lt_summaries}")
                
                # Recent (Last 10 notes)
                recent_notes_res = await db.execute(
                    select(Note.title, Note.summary)
                    .where(Note.user_id == user.id, Note.id != note_id, Note.summary.isnot(None))
                    .order_by(Note.created_at.desc())
                    .limit(10)
                )
                recent_notes = recent_notes_res.all()
                if recent_notes:
                    recent_str = "\n".join([f"- {r.title}: {r.summary[:100]}" for r in recent_notes])
                    ctx_parts.append(f"Recent context: {recent_str}")

            dynamic_prompt = "\n".join(ctx_parts)
            
            # --- TOKEN MANAGEMENT / TRUNCATION (Requirement) ---
            token_count = len(dynamic_prompt) // 4
            if token_count > 800:
                logger.warning(f"Context truncated to ~{token_count} tokens for user {user.id}")
                pruned_parts = []
                if user and user.identity_summary:
                    pruned_parts.append(f"User identity: {user.identity_summary}")
                
                if lt_summaries and "No long-term" not in lt_summaries:
                    pruned_parts.append(f"Long-term knowledge (Trimmed): {lt_summaries[:1000]}")
                
                if recent_notes:
                    # Stricter trim for recent if total is still too high
                    recent_str = "\n".join([f"- {r.title}: {r.summary[:50]}" for r in recent_notes])
                    pruned_parts.append(f"Recent context (Trimmed): {recent_str}")
                
                dynamic_prompt = "\n".join(pruned_parts)
                logger.info(f"Context truncated to ~{len(dynamic_prompt)//4} tokens")
            
            # 4. Call AI
            analysis = await ai_service.analyze_text(
                note.transcription_text,
                user_context=dynamic_prompt,
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
        
        # Trigger reflection
        from workers.reflection_tasks import reflection_incremental
        reflection_incremental.delay(note.user_id)

@celery.task(name="analyze.process_note", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_analyze(note_id: str):
    async_to_sync(_process_analyze_async)(note_id)
    return {"status": "completed", "note_id": note_id}
