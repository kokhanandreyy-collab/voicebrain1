from typing import Dict, Any, List, Optional
from loguru import logger
from asgiref.sync import async_to_sync
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery
from app.services.ai_service import ai_service
from app.models import Note, User, NoteEmbedding
from app.core.database import AsyncSessionLocal
from app.core.types import AIAnalysisPack

async def step_analyze(text: str, user_context: Optional[str] = None, target_language: str = "Original") -> Dict[str, Any]:
    return await ai_service.analyze_text(text, user_context=user_context, target_language=target_language)

async def step_embed_and_save(note: Note, text: str, analysis: Dict[str, Any], db: AsyncSession) -> None:
    note.title = analysis.get("title", "Untitled Note")
    note.summary = analysis.get("summary")
    note.action_items = analysis.get("action_items", [])
    note.calendar_events = analysis.get("calendar_events", [])
    note.tags = analysis.get("tags", [])
    note.diarization = analysis.get("diarization", [])
    note.mood = analysis.get("mood", "Neutral")
    note.health_data = analysis.get("health_data")
    
    note.ai_analysis = AIAnalysisPack(
        intent=analysis.get("intent", "note"),
        suggested_project=analysis.get("suggested_project", "Inbox"),
        entities=analysis.get("entities", []),
        priority=analysis.get("priority", 4),
        notion_properties=analysis.get("notion_properties", {}),
        explicit_destination_app=analysis.get("explicit_destination_app"),
        explicit_folder=analysis.get("explicit_folder")
    )
    
    search_content = f"{note.title} {note.summary} {text} {' '.join(note.tags)}"
    try:
        vector = await ai_service.generate_embedding(search_content)
        note_embedding = NoteEmbedding(note_id=note.id, embedding=vector)
        db.add(note_embedding)
    except Exception as e:
        logger.error(f"Embedding failed: {e}")



from sqlalchemy import desc
from app.utils.redis import short_term_memory
from app.models import LongTermSummary

async def step_get_medium_term_context(user_id: str, note_id: str, text: str, db: AsyncSession) -> str:
    """Fetch top 5 similar notes (Medium-Term Memory)."""
    try:
        query_vector = await ai_service.generate_embedding(text)
        result = await db.execute(
            select(Note)
            .join(NoteEmbedding)
            .where(Note.user_id == user_id, Note.id != note_id)
            .order_by(NoteEmbedding.embedding.cosine_distance(query_vector))
            .limit(5)
        )
        notes = list(result.scalars().all())
        
        context_parts = []
        for n in notes:
            # Mask sensitive or too long content
            summary_part = n.summary[:300] if n.summary else "No summary"
            context_parts.append(f"Note: {n.title}\nSummary: {summary_part}")
        
        return "\n".join(context_parts) if context_parts else "No recent related context found."
    except Exception as e:
        logger.error(f"Medium-Term retrieval failed: {e}")
        return ""

async def step_get_long_term_memory(user_id: str, db: AsyncSession) -> str:
    """Fetch top 3 high-importance long-term summaries."""
    try:
        result = await db.execute(
            select(LongTermSummary)
            .where(LongTermSummary.user_id == user_id)
            .order_by(desc(LongTermSummary.importance_score))
            .limit(3)
        )
        summaries = list(result.scalars().all())
        parts = [f"- {s.summary_text}" for s in summaries]
        return "\n".join(parts) if parts else "No long-term knowledge recorded yet."
    except Exception as e:
        logger.error(f"Long-Term retrieval failed: {e}")
        return ""

async def _process_analyze_async(note_id: str) -> None:
    logger.info(f"[Analyze] Processing note: {note_id}")
    db = AsyncSessionLocal()
    try:
        result = await db.execute(select(Note).where(Note.id == note_id))
        note = result.scalars().first()
        if not note: return

        # 1. Fetch User Data
        user_bio: Optional[str] = None
        target_lang: str = "Original"
        u_res = await db.execute(select(User).where(User.id == note.user_id))
        user = u_res.scalars().first()
        if user:
            user_bio, target_lang = user.bio, user.target_language or "Original"

        # 2. Fetch Hierarchical Memory
        note.processing_step = "🧠 Recalling memories..."
        await db.commit()

        # Short-Term (Redis list of last 10 actions/messages)
        st_history = await short_term_memory.get_history(note.user_id)
        short_term_str = "\n".join([f"- {item.get('text', str(item))}" for item in st_history]) if st_history else "No recent history."

        # Medium-Term (Semantic Search)
        medium_term_str = await step_get_medium_term_context(note.user_id, note.id, note.transcription_text, db)

        # Long-Term (High Importance Summaries)
        long_term_str = await step_get_long_term_memory(note.user_id, db)

        # 3. Format Combined Context
        hierarchical_context = (
            f"Short-term (Last actions):\n{short_term_str}\n\n"
            f"Recent context (Related notes):\n{medium_term_str}\n\n"
            f"Long-term knowledge (General themes):\n{long_term_str}"
        )

        # 4. Analyze with Context
        note.processing_step = "🤖 AI Analysis..."
        await db.commit()
        
        analysis = await ai_service.analyze_text(
            note.transcription_text, 
            user_context=user_bio, 
            target_language=target_lang,
            previous_context=hierarchical_context
        )

        # 5. Save results and trigger next stage
        await step_embed_and_save(note, note.transcription_text, analysis, db)
        
        # Track this analysis as a short-term action for future context
        await short_term_memory.add_action(note.user_id, {
            "type": "note_analyzed",
            "title": analysis.get("title"),
            "text": f"Analyzed note: {analysis.get('title')}. Summary: {analysis.get('summary')[:100]}..."
        })
        
        note.processing_step = "🚀 Syncing with apps..."
        await db.commit()
        
        # Trigger Next Stage
        from workers.sync_tasks import process_sync
        process_sync.delay(note_id)
        
    except Exception as e:
        logger.error(f"Analyze task failed for {note_id}: {e}")
        from workers.common_tasks import handle_note_failure
        await handle_note_failure(note_id, str(e))
    finally:
        await db.close()

@celery.task(name="analyze.process_note")
def process_analyze(note_id: str):
    async_to_sync(_process_analyze_async)(note_id)
    return {"status": "analyzed", "note_id": note_id}
