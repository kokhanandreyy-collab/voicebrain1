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
    2. Extract graph-like relations (ENA).
    3. Save results.
    """
    logger.info(f"Starting graph-based reflection for user {user_id}")
    async with AsyncSessionLocal() as db:
        # 1. Fetch recent notes
        result = await db.execute(
            select(Note)
            .where(Note.user_id == user_id)
            .order_by(desc(Note.created_at))
            .limit(50)
        )
        notes = result.scalars().all()
        if not notes:
            return

        notes_data = [{"id": n.id, "text": n.transcription_text[:500]} for n in notes]
        notes_text = "\n".join([f"ID: {n['id']} | Content: {n['text']}" for n in notes_data])

        # 2. Step A: Summary and Importance
        prompt = (
            "Analyze the following notes. Provide a consolidated summary and an importance score (0-10).\n"
            "Return JSON: {'summary': '...', 'importance_score': float}\n\n"
            f"Notes:\n{notes_text[:4000]}"
        )
        
        resp = await ai_service.get_chat_completion([
            {"role": "system", "content": "You are a memory analyst. Return JSON."},
            {"role": "user", "content": prompt}
        ])
        
        try:
            data = json.loads(ai_service.clean_json_response(resp))
            summary = data.get("summary")
            score = float(data.get("importance_score", 5.0))
            
            # Save LongTermMemory
            if summary:
                emb = await ai_service.generate_embedding(summary)
                memory = LongTermMemory(
                    user_id=user_id,
                    summary_text=summary,
                    embedding=emb,
                    importance_score=score
                )
                db.add(memory)
        except Exception as e:
            logger.error(f"Reflection summary failed: {e}")

        # 3. Step B: Graph Extraction (ENA)
        rel_prompt = (
            "Analyze the relationships between these notes based on context, causality, and contradictions.\n"
            "Return a JSON list of relations: [{'note1_id': str, 'note2_id': str, 'relation_type': 'caused|related|updated|contradicted', 'strength': float (0.1-1.0)}]\n"
            f"\nNotes list:\n{json.dumps(notes_data, ensure_ascii=False)}"
        )
        
        rel_resp = await ai_service.get_chat_completion([
            {"role": "system", "content": "You are a graph relationship extractor. Return ONLY a JSON list."},
            {"role": "user", "content": rel_prompt}
        ])
        
        try:
            relations = json.loads(ai_service.clean_json_response(rel_resp))
            new_rels = []
            for r in relations:
                new_rels.append(NoteRelation(
                    note_id1=r.get("note1_id"),
                    note_id2=r.get("note2_id"),
                    relation_type=r.get("relation_type", "related"),
                    strength=float(r.get("strength", 1.0))
                ))
            if new_rels:
                db.add_all(new_rels)
                logger.info(f"Extracted {len(new_rels)} relations for user {user_id}")
        except Exception as e:
            logger.error(f"Graph extraction failed: {e}")

        await db.commit()

@shared_task(name="reflection_daily")
def reflection_daily(user_id: str):
    """Celery task for daily reflection and graph building."""
    async_to_sync(_process_reflection_async)(user_id)
