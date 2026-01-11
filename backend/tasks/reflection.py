from celery import shared_task
from sqlalchemy.future import select
from sqlalchemy import desc, func
from loguru import logger
import datetime
import json
import math
from asgiref.sync import async_to_sync

from infrastructure.database import AsyncSessionLocal
from app.models import User, Note, LongTermMemory, NoteRelation
from app.services.ai_service import ai_service
from infrastructure.monitoring import monitor
from infrastructure.config import settings

def _calculate_composite_importance(base_score: float, ref_count: int, note_count: int, has_actions: bool, avg_days: float) -> float:
    """
    Calculates a weighted importance score.
    Weights from settings (default: 0.6, 0.1, 0.1, 0.1, 0.1)
    """
    # Normalize components to 0-10 scale
    s_refs = min(10.0, float(ref_count) * 2.0) # 5 refs = 10 pts
    s_recurrence = min(10.0, float(note_count) / 3.0) # 30 notes = 10 pts
    s_actions = 10.0 if has_actions else 0.0
    s_time = max(0.0, 10.0 - avg_days) # fresh = 10 pts
    
    comp = (
        base_score * settings.IMP_WEIGHT_BASE +
        s_refs * settings.IMP_WEIGHT_REFS +
        s_recurrence * settings.IMP_WEIGHT_RECURRENCE +
        s_actions * settings.IMP_WEIGHT_ACTIONS +
        s_time * settings.IMP_WEIGHT_TIME
    )
    return round(min(10.0, comp), 2)

async def _process_reflection_async(user_id: str):
    """
    Refactored Multi-Step Reflection with Composite Importance:
    Step 1: Condensation (Facts only)
    Step 2: Pattern Extraction (Identity/Habits)
    Step 3: Narrative Linking (Graph)
    Final: Importance Calculation & Save
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

        # Pre-calculate stats for composite score
        note_count = len(all_notes)
        has_actions = any(len(n.action_items or []) > 0 for n in all_notes)
        
        now = datetime.datetime.now(datetime.timezone.utc)
        total_days = 0
        for n in all_notes:
            created = n.created_at.replace(tzinfo=datetime.timezone.utc) if n.created_at.tzinfo is None else n.created_at
            total_days += (now - created).total_seconds() / (24 * 3600)
        avg_days = total_days / note_count if note_count > 0 else 0

        notes_data = [{"id": n.id, "text": n.transcription_text[:500], "score": n.importance_score or 0} for n in all_notes]
        notes_text = "\n".join([f"ID: {n['id']} | Content: {n['text']}" for n in notes_data])

        # --- STEP 1: FACT CONDENSATION ---
        facts = ""
        base_score = 5.0
        fact_prompt = (
            "Extract only factual events, data points, and specific actions from these notes. "
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
            base_score = float(data1.get("importance_score", 5.0))
        except Exception as e:
            logger.error(f"Reflection Step 1 failed: {e}")

        # --- STEP 2: PATTERN EXTRACTION ---
        # --- STEP 2: PATTERN EXTRACTION ---
        pattern_prompt = (
            "Analyze these notes for recurring patterns, communication style, and apparent emotional state. "
            "Return JSON: {'stable_identity': '...', 'volatile_preferences': {...}, 'current_emotion': '...'}\n\n"
            f"Notes:\n{notes_text[:4000]}"
        )
        
        try:
            resp2 = await ai_service.get_chat_completion([
                {"role": "system", "content": "You are a behavioral psychologist. Return JSON."},
                {"role": "user", "content": pattern_prompt}
            ])
            data2 = json.loads(ai_service.clean_json_response(resp2))
            
            # 1. Update Volatile Preferences (Always)
            user.volatile_preferences = data2.get("volatile_preferences", {})
            
            # 2. Append Emotion Logic (Append-only)
            emotion = data2.get("current_emotion")
            if emotion:
                if not user.emotion_history:
                    user.emotion_history = []
                # Simple append, maybe limit size in real prod, but per req just append
                # Create a local copy to modify (SQLAlchemy Mutable handling quirk sometimes)
                history = list(user.emotion_history) 
                history.append({"date": datetime.datetime.now().isoformat(), "emotion": emotion})
                user.emotion_history = history[-50:] # Keep last 50 to avoid infinite growth

            # 3. Gated Identity Update
            new_identity = data2.get("stable_identity", "")
            should_update = False
            
            if not user.stable_identity:
                should_update = True
            elif new_identity:
                # Calculate similarity
                new_emb = await ai_service.generate_embedding(new_identity)
                if user.identity_embedding:
                    # Cosine Sim
                    def cosine_sim(v1, v2):
                         dot = sum(a*b for a, b in zip(v1, v2))
                         norm1 = math.sqrt(sum(a*a for a in v1))
                         norm2 = math.sqrt(sum(b*b for b in v2))
                         return dot / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0
                    
                    sim = cosine_sim(user.identity_embedding, new_emb)
                    logger.info(f"Identity Similarity: {sim}")
                    
                    if sim < 0.85: # Threshold
                        should_update = True
                else:
                    should_update = True
                    
            if should_update and new_identity:
                user.stable_identity = new_identity
                user.identity_embedding = await ai_service.generate_embedding(new_identity)
                logger.info("Stable Identity Updated (Gated)")
                
        except Exception as e:
            logger.error(f"Reflection Step 2 failed: {e}")

        # --- STEP 3: NARRATIVE LINKING ---
        new_rels_count = 0
        high_importance_notes = [n for n in all_notes if (n.importance_score or 0) >= 7]
        if high_importance_notes:
            hi_notes_data = [{"id": n.id, "text": n.transcription_text[:500]} for n in high_importance_notes]
            rel_prompt = (
                "Link these high-importance notes into a narrative thread. "
                "Return JSON list: [{'note1_id': str, 'note2_id': str, 'relation_type': '...', 'strength': float}]\n"
                f"Notes:\n{json.dumps(hi_notes_data, ensure_ascii=False)}"
            )
            
            try:
                resp3 = await ai_service.get_chat_completion([
                    {"role": "system", "content": "You are a narrative architect. Return JSON list."},
                    {"role": "user", "content": rel_prompt}
                ])
                relations = json.loads(ai_service.clean_json_response(resp3))
                for r in relations:
                    db.add(NoteRelation(
                        note_id1=r.get("note1_id"),
                        note_id2=r.get("note2_id"),
                        relation_type=r.get("relation_type", "related"),
                        strength=float(r.get("strength", 1.0))
                    ))
                    new_rels_count += 1
            except Exception as e:
                logger.error(f"Reflection Step 3 failed: {e}")

        # --- FINAL: SAVE MEMORY WITH COMPOSITE SCORE ---
        if facts:
            comp_score = _calculate_composite_importance(
                base_score=base_score,
                ref_count=new_rels_count,
                note_count=note_count,
                has_actions=has_actions,
                avg_days=avg_days
            )
            
            emb = await ai_service.generate_embedding(facts)
            memory = LongTermMemory(
                user_id=user_id,
                summary_text=facts,
                embedding=emb,
                importance_score=comp_score
            )
            db.add(memory)
            logger.info(f"Composite Reflection saved for {user_id}. Base: {base_score}, Final: {comp_score}")

        await db.commit()

@shared_task(name="reflection_daily")
def reflection_daily(user_id: str):
    async_to_sync(_process_reflection_async)(user_id)
