from celery import shared_task
from sqlalchemy.future import select
from sqlalchemy import desc, func
from loguru import logger
import datetime
import json
from asgiref.sync import async_to_sync

from infrastructure.database import AsyncSessionLocal
from app.models import User, Note, LongTermMemory, NoteRelation
from app.services.ai_service import ai_service
from infrastructure.monitoring import monitor

async def _process_reflection_async(user_id: str):
    """
    Refactored Multi-Step Reflection:
    Step 1: Condensation (Facts only)
    Step 2: Pattern Extraction (Identity/Habits)
    Step 3: Narrative Linking (Graph)
    """
    logger.info(f"Starting multi-step reflection for user {user_id}")
    async with AsyncSessionLocal() as db:
        # Monitoring
        total_notes = (await db.execute(select(func.count(Note.id)))).scalar()
        total_rels = (await db.execute(select(func.count(NoteRelation.id)))).scalar()
        monitor.update_graph_metrics(total_notes, total_rels)
        monitor.update_hit_rate()

        # Fetch user
        user_res = await db.execute(select(User).where(User.id == user_id))
        user = user_res.scalars().first()
        if not user: return

        # Fetch recent notes
        result = await db.execute(
            select(Note)
            .where(Note.user_id == user_id)
            .order_by(desc(Note.created_at))
            .limit(50)
        )
        all_notes = result.scalars().all()
        if not all_notes: return

        notes_data = [{"id": n.id, "text": n.transcription_text[:500], "score": n.importance_score or 0} for n in all_notes]
        notes_text = "\n".join([f"ID: {n['id']} | Content: {n['text']}" for n in notes_data])

        # --- STEP 1: FACT CONDENSATION ---
        # Objective: Only facts and events, no conclusions.
        fact_prompt = (
            "Extract only factual events, data points, and specific actions from these notes. "
            "Do not provide interpretations, conclusions, or emotional analysis. "
            "Focus on 'what happened'.\n\n"
            "Return JSON: {'facts_summary': str, 'importance_score': float}\n\n"
            f"Notes:\n{notes_text[:4000]}"
        )
        
        try:
            resp1 = await ai_service.get_chat_completion([
                {"role": "system", "content": "You are a factual data extractor. Return JSON."},
                {"role": "user", "content": fact_prompt}
            ])
            data1 = json.loads(ai_service.clean_json_response(resp1))
            facts = data1.get("facts_summary")
            if facts:
                emb = await ai_service.generate_embedding(facts)
                memory = LongTermMemory(
                    user_id=user_id,
                    summary_text=facts,
                    embedding=emb,
                    importance_score=float(data1.get("importance_score", 5.0))
                )
                db.add(memory)
                logger.debug(f"Step 1: Facts condensed for {user_id}")
        except Exception as e:
            logger.error(f"Reflection Step 1 failed: {e}")

        # --- STEP 2: PATTERN EXTRACTION ---
        # Objective: Habits, communication style, stable/volatile traits.
        pattern_prompt = (
            "Analyze these notes for recurring patterns, habits, and communication gaya/style. "
            "Update the user's stable identity traits and identify their current volatile focus/mood.\n\n"
            "Return JSON: {\n"
            "  'stable_identity': 'consolidated long-term traits',\n"
            "  'volatile_preferences': {'current_focus': '...', 'mood': '...'}\n"
            "}\n\n"
            f"Notes:\n{notes_text[:4000]}"
        )
        
        try:
            resp2 = await ai_service.get_chat_completion([
                {"role": "system", "content": "You are a behavioral psychologist and pattern analyst. Return JSON."},
                {"role": "user", "content": pattern_prompt}
            ])
            data2 = json.loads(ai_service.clean_json_response(resp2))
            user.volatile_preferences = data2.get("volatile_preferences", {})
            
            is_sunday = datetime.datetime.now().weekday() == 6
            if not user.stable_identity or is_sunday:
                user.stable_identity = data2.get("stable_identity", "")
            logger.debug(f"Step 2: Patterns extracted for {user_id}")
        except Exception as e:
            logger.error(f"Reflection Step 2 failed: {e}")

        # --- STEP 3: NARRATIVE LINKING ---
        # Objective: Connect high-score notes via narrative threads.
        high_importance_notes = [n for n in all_notes if (n.importance_score or 0) >= 7]
        if high_importance_notes:
            hi_notes_data = [{"id": n.id, "text": n.transcription_text[:500]} for n in high_importance_notes]
            rel_prompt = (
                "Link these high-importance notes into a narrative thread. "
                "Find relationships (caused|related|updated) and assign strength (0.0 - 1.0).\n\n"
                "Return JSON list: [{'note1_id': str, 'note2_id': str, 'relation_type': '...', 'strength': float}]\n"
                f"Notes:\n{json.dumps(hi_notes_data, ensure_ascii=False)}"
            )
            
            try:
                resp3 = await ai_service.get_chat_completion([
                    {"role": "system", "content": "You are a narrative architect. Connect the dots. Return JSON list."},
                    {"role": "user", "content": rel_prompt}
                ])
                relations = json.loads(ai_service.clean_json_response(resp3))
                new_rels_count = 0
                for r in relations:
                    db.add(NoteRelation(
                        note_id1=r.get("note1_id"),
                        note_id2=r.get("note2_id"),
                        relation_type=r.get("relation_type", "related"),
                        strength=float(r.get("strength", 1.0))
                    ))
                    new_rels_count += 1
                logger.info(f"Step 3: Narrative links for {user_id}: {new_rels_count} relations.")
            except Exception as e:
                logger.error(f"Reflection Step 3 failed: {e}")

        await db.commit()

@shared_task(name="reflection_daily")
def reflection_daily(user_id: str):
    async_to_sync(_process_reflection_async)(user_id)
