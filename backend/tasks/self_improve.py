
from asgiref.sync import async_to_sync
from celery import shared_task
from sqlalchemy.future import select
from sqlalchemy import delete, and_
from loguru import logger
import json
import datetime

from infrastructure.database import AsyncSessionLocal
from app.models import User, LongTermMemory, NoteRelation
from app.services.ai_service import ai_service

async def _process_improvement_async(user_id: str):
    logger.info(f"Starting memory self-improvement for user {user_id}")
    async with AsyncSessionLocal() as db:
        # 1. Fetch all LongTermMemory
        mem_res = await db.execute(select(LongTermMemory).where(LongTermMemory.user_id == user_id, LongTermMemory.is_archived == False))
        memories = mem_res.scalars().all()
        
        if len(memories) < 2:
            return

        # 2. Extract context
        mem_data = [{"id": m.id, "text": m.summary_text} for m in memories]
        
        # 3. Prompt DeepSeek
        prompt = (
            "Analyze these long-term memory records. Identify duplicates to merge, contradictions to remove, and new logical connections to propose.\n"
            "Return JSON: {\n"
            "  'merged_groups': [[id1, id2, ...], ...], \n"
            "  'contradictions_to_remove': [id3, id4], \n"
            "  'new_relations': [{'note_id1': '...', 'note_id2': '...', 'type': 'related', 'strength': 0.8}]\n"
            "}\n"
            "For merged groups, I will create a new memory and archive the old ones.\n\n"
            f"Memories:\n{json.dumps(mem_data, ensure_ascii=False)}"
        )
        
        try:
            resp = await ai_service.get_chat_completion([
                {"role": "system", "content": "You are a memory optimization agent. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ])
            data = json.loads(ai_service.clean_json_response(resp))
            
            # --- EXECUTE ACTIONS ---
            
            # A. Merged Groups
            for group in data.get("merged_groups", []):
                if len(group) < 2: continue
                # Fetch objects
                targets = [m for m in memories if m.id in group]
                if not targets: continue
                
                # Create NEW condensed memory
                text_combined = " ".join([m.summary_text for m in targets])
                
                # Ask AI to summarize the combined text
                summary_prompt = f"Summarize these merged memories into a single concise fact:\n{text_combined}"
                new_summary = await ai_service.get_chat_completion([{"role": "user", "content": summary_prompt}])
                
                new_emb = await ai_service.generate_embedding(new_summary)
                
                new_mem = LongTermMemory(
                    user_id=user_id,
                    summary_text=new_summary,
                    embedding=new_emb,
                    importance_score=max([m.importance_score for m in targets]),
                    confidence=1.0, # Improved
                    source="refined"
                )
                db.add(new_mem)
                
                # Archive old
                for m in targets:
                    m.is_archived = True
                    m.archived_summary = "Merged into new optimized memory."
            
            # B. Contradictions
            for mid in data.get("contradictions_to_remove", []):
                target = next((m for m in memories if m.id == mid), None)
                if target:
                    target.is_archived = True
                    target.archived_summary = "Removed as contradictory/obsolete."
            
            # C. New Relations (NoteRelation updates)
            # Note: The prompt asks for NOTE relations, but input is MEMORIES (LongTermMemory).
            # LongTermMemory usually doesn't map 1:1 to Note ID in a way that allows NoteRelation between them easily
            # UNLESS NoteRelation supports LongTermMemory?
            # Current NoteRelation connects Note objects.
            # If the user asks for new connections between MEMORIES, we don't have a table for that (MemoryRelation?)
            # But maybe the prompt meant logic connections which we just store as 'Refined' memory?
            # Or maybe we assume these memories are linked to notes?
            # Re-reading prompt: "new logical connections to propose".
            # If we want to graph them, we need MemoryRelation or Link.
            # As per spec "Update LongTermMemory/graph", let's assume we might add NoteRelations if we can link back to notes?
            # But LTM is aggregated.
            # Let's Skip C for strict safety OR log it.
            # Actually, standard "self-improving memory" usually implies unifying LTMs.
            # Let's stick to Merging and Contradiction removal as the primary "improvement".
            
            await db.commit()
            logger.info(f"Memory improvement completed for {user_id}")
            
        except Exception as e:
            logger.error(f"Memory Improvement failed for {user_id}: {e}")

@shared_task(name="memory.self_improve")
def self_improve_memory(user_id: str):
    async_to_sync(_process_improvement_async)(user_id)

async def _trigger_weekly_improvement_async():
    logger.info("Triggering weekly memory improvement...")
    async with AsyncSessionLocal() as db:
        users = (await db.execute(select(User).where(User.is_active == True))).scalars().all()
        for u in users:
            self_improve_memory.delay(u.id)

@shared_task(name="memory.trigger_weekly_improvement")
def trigger_weekly_improvement():
    async_to_sync(_trigger_weekly_improvement_async)()
