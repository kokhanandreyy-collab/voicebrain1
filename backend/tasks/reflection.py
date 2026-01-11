from celery import shared_task
from sqlalchemy.future import select
from sqlalchemy import desc
from loguru import logger
import datetime
import json
from asgiref.sync import async_to_sync

from infrastructure.database import AsyncSessionLocal
from app.models import User, Note, LongTermMemory, NoteRelation
from app.services.ai_service import ai_service

async def _process_reflection_async(user_id: str):
    """
    1. Summarize last 50 notes.
    2. Extract graph-like relations (ENA) for high-importance notes.
    3. Update user identity (Stable vs Volatile).
    """
    logger.info(f"Starting graph-based reflection for user {user_id}")
    async with AsyncSessionLocal() as db:
        # Fetch user
        user_res = await db.execute(select(User).where(User.id == user_id))
        user = user_res.scalars().first()
        if not user:
            return

        # 1. Fetch recent notes
        result = await db.execute(
            select(Note)
            .where(Note.user_id == user_id)
            .order_by(desc(Note.created_at))
            .limit(50)
        )
        all_notes = result.scalars().all()
        if not all_notes:
            return

        notes_data = [{"id": n.id, "text": n.transcription_text[:500]} for n in all_notes]
        notes_text = "\n".join([f"ID: {n['id']} | Content: {n['text']}" for n in notes_data])

        # 2. Summary and Identity Analysis
        prompt = (
            "Analyze the following notes. Provide:\n"
            "1. Consolidated summary and importance score.\n"
            "2. STABLE IDENTITY: Long-term traits, communication style, core values.\n"
            "3. VOLATILE PREFERENCES: Current focus, temporary priorities.\n"
            "Return JSON: {\n"
            "  'summary': '...',\n"
            "  'importance_score': float,\n"
            "  'stable_identity': '...',\n"
            "  'volatile_preferences': {...}\n"
            "}\n\n"
            f"Notes:\n{notes_text[:4000]}"
        )
        
        resp = await ai_service.get_chat_completion([
            {"role": "system", "content": "You are a user identity analyst. Return JSON."},
            {"role": "user", "content": prompt}
        ])
        
        try:
            data = json.loads(ai_service.clean_json_response(resp))
            summary = data.get("summary")
            if summary:
                emb = await ai_service.generate_embedding(summary)
                memory = LongTermMemory(
                    user_id=user_id,
                    summary_text=summary,
                    embedding=emb,
                    importance_score=float(data.get("importance_score", 5.0))
                )
                db.add(memory)

            user.volatile_preferences = data.get("volatile_preferences", {})
            is_sunday = datetime.datetime.now().weekday() == 6
            if not user.stable_identity or is_sunday:
                user.stable_identity = data.get("stable_identity", "")

        except Exception as e:
            logger.error(f"Reflection identity update failed: {e}")

        # 3. Graph Extraction (ENA) - Filter by importance_score >= 7
        high_importance_notes = [n for n in all_notes if (n.importance_score or 0) >= 7]
        if high_importance_notes:
            hi_notes_data = [{"id": n.id, "text": n.transcription_text[:500]} for n in high_importance_notes]
            rel_prompt = (
                "Analyze relationships between these high-importance notes.\n"
                "Return JSON list: [{'note1_id': str, 'note2_id': str, 'relation_type': 'caused|related|updated', 'strength': float}]\n"
                f"\nNotes:\n{json.dumps(hi_notes_data, ensure_ascii=False)}"
            )
            
            try:
                rel_resp = await ai_service.get_chat_completion([
                    {"role": "system", "content": "Return JSON list."},
                    {"role": "user", "content": rel_prompt}
                ])
                relations = json.loads(ai_service.clean_json_response(rel_resp))
                new_rels_count = 0
                for r in relations:
                    db.add(NoteRelation(
                        note_id1=r.get("note1_id"),
                        note_id2=r.get("note2_id"),
                        relation_type=r.get("relation_type", "related"),
                        strength=float(r.get("strength", 1.0))
                    ))
                    new_rels_count += 1
                logger.info(f"Graph extraction for user {user_id}: saved {new_rels_count} relations.")
            except Exception as e:
                logger.error(f"Graph extraction failed: {e}")

        await db.commit()

@shared_task(name="reflection_daily")
def reflection_daily(user_id: str):
    async_to_sync(_process_reflection_async)(user_id)
