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
    logger.info(f"Starting dynamic analysis for note {note_id}")
    async with AsyncSessionLocal() as db:
        # 1. Fetch Note and User
        res_note = await db.execute(select(Note).where(Note.id == note_id))
        note = res_note.scalars().first()
        if not note or not note.transcription_text: return

        res_user = await db.execute(select(User).where(User.id == note.user_id))
        user = res_user.scalars().first()
        
        # 2. Semantic Cache Check (pgvector)
        current_embedding = await ai_service.generate_embedding(note.transcription_text)
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
            logger.warning(f"Semantic Cache lookup failed: {e}")

        if cached_entry:
            analysis = cached_entry.result
            logger.info(f"Semantic Cache hit: using cached result for {note_id}")
            track_cache_hit("note_analysis")
        else:
            track_cache_miss("note_analysis")
            
            # 3. Build Dynamic Context using Decomposed Service
            lt_summaries = ""
            recent_notes = []
            
            if user:
                # Fetch Memories for RAG
                lt_summaries = await rag_service.get_long_term_memory(user.id, db)
                
                recent_res = await db.execute(
                    select(Note.title, Note.summary)
                    .where(Note.user_id == user.id, Note.id != note_id, Note.summary.isnot(None))
                    .order_by(Note.created_at.desc())
                    .limit(10)
                )
                recent_notes = recent_res.all()
                recent_str = "\n".join([f"- {r.title}: {r.summary[:100]}" for r in recent_notes])

                # Use Decomposed AIService Builder to handle Truncation/Formatting
                dynamic_context = ai_service.builder.truncate_context(
                    identity=user.identity_summary or "",
                    preferences=user.adaptive_preferences or {},
                    long_term=lt_summaries,
                    recent_context=recent_str
                )
            else:
                dynamic_context = ""

            # 4. Orchestrated Analysis Call
            analysis = await ai_service.analyze_text(
                note.transcription_text,
                user_context=dynamic_context,
                target_language=user.target_language if user else "Original"
            )
            
            # 5. Save to Semantic Cache
            try:
                ttl = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
                db.add(CachedAnalysis(
                    user_id=note.user_id,
                    embedding=current_embedding,
                    result=analysis,
                    expires_at=ttl
                ))
            except Exception as e:
                logger.warning(f"Failed to save semantic cache: {e}")

        # 6. Apply Analysis and Completion
        analyze_core._apply_analysis_to_note(note, analysis)
        note.status = NoteStatus.ANALYZED
        await db.commit()
        
        # Trigger follow-up Reflection
        from workers.reflection_tasks import reflection_incremental
        reflection_incremental.delay(note.user_id)

@celery.task(name="analyze.process_note", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_analyze(note_id: str):
    async_to_sync(_process_analyze_async)(note_id)
    return {"status": "completed", "note_id": note_id}
