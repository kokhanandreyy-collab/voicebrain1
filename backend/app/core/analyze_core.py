from typing import Dict, Any, List, Optional
from loguru import logger
from sqlalchemy.future import select
from sqlalchemy import desc, update
from sqlalchemy.ext.asyncio import AsyncSession
import datetime
import json
import hashlib

from app.models import Note, User, CachedAnalysis, CachedIntent
from app.services.ai_service import ai_service
from .rag_service import rag_service
from infrastructure.monitoring import monitor

class AnalyzeCore:
    async def _check_intent_cache(self, text: str, user_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """Checks if a simple command has a cached action result."""
        # 1. Classification (Simple regex for example)
        intent = None
        params = {}
        if text.lower().startswith("запиши задачу:"):
            intent = "create_task"
            params = {"text": text[14:].strip()}
        elif text.lower().startswith("добавь встречу:"):
            intent = "add_event"
            params = {"text": text[15:].strip()}
            
        if not intent: return None
        
        # 2. Key: hash(intent + params)
        key_raw = f"{intent}:{json.dumps(params, sort_keys=True)}"
        intent_key = hashlib.sha256(key_raw.encode()).hexdigest()
        
        # 3. Lookup
        res = await db.execute(
            select(CachedIntent).where(
                CachedIntent.user_id == user_id,
                CachedIntent.intent_key == intent_key,
                CachedIntent.expires_at > datetime.datetime.now(datetime.timezone.utc)
            )
        )
        entry = res.scalars().first()
        if entry:
            logger.info(f"Intent Cache Hit: {intent_key}")
            monitor.track_cache_hit("intent")
            return entry.action_json
        return None

    async def _save_intent_cache(self, text: str, user_id: str, analysis: Dict[str, Any], db: AsyncSession):
        """Saves simple intent results to cache (TTL 7 days)."""
        intent = analysis.get("intent")
        if intent not in ["create_task", "add_event"]: return
        
        params = {"text": text.split(":")[-1].strip() if ":" in text else text}
        key_raw = f"{intent}:{json.dumps(params, sort_keys=True)}"
        intent_key = hashlib.sha256(key_raw.encode()).hexdigest()
        
        ttl = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
        new_cache = CachedIntent(
            id=str(datetime.datetime.now().timestamp()), # dummy ID if needed
            user_id=user_id,
            intent_key=intent_key,
            action_json=analysis,
            expires_at=ttl
        )
        db.add(new_cache)

    async def analyze_step(self, note: Note, user: Optional[User], db: AsyncSession, memory_service: Any) -> tuple[Dict[str, Any], bool]:
        """Orchestrates RAG context, multiple cache levels, and DeepSeek analysis."""
        user_bio = (user.bio or "") if user else ""
        
        # 1. Identity & Style Context
        if user and user.stable_identity:
            user_bio = f"{user_bio}\n\nStable Identity: {user.stable_identity}".strip()

        if user and user.volatile_preferences:
            v_prefs = json.dumps(user.volatile_preferences, indent=2)
            user_bio += f"\n\nVolatile focus: {v_prefs} (Use if relevant to intent)."

        # 2. Memory Context (RAG)
        hierarchical_context = await rag_service.build_hierarchical_context(note, db, memory_service)
        
        cache_hit = False
        analysis = None
        
        # 3. Intent Cache (Fastest)
        intent_cached = await self._check_intent_cache(note.transcription_text, note.user_id, db)
        if intent_cached:
            analysis = intent_cached
            cache_hit = True
        
        # 4. Semantic Cache (Contextual)
        if not cache_hit:
            current_embedding = await ai_service.generate_embedding(note.transcription_text)
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
                analysis = cached_entry.result
                cache_hit = True
                monitor.track_cache_hit("semantic")

        # 5. DeepSeek Call (Fallback)
        if not cache_hit:
            target_lang = user.target_language if user else "Original"
            analysis = await ai_service.analyze_text(
                note.transcription_text,
                user_context=user_bio,
                target_language=target_lang,
                previous_context=hierarchical_context
            )
            # Save levels
            await self._save_intent_cache(note.transcription_text, note.user_id, analysis, db)
            
            emb = await ai_service.generate_embedding(note.transcription_text)
            ttl = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
            db.add(CachedAnalysis(user_id=note.user_id, embedding=emb, result=analysis, expires_at=ttl))
            monitor.track_cache_miss("all")

        # 6. Apply & Finalize
        self._apply_analysis_to_note(note, analysis)
        
        # Emotional snapshot
        if user:
            new_mood = analysis.get("mood", "Neutral")
            hist = list(user.emotion_history or [])
            hist.append({"mood": new_mood, "date": datetime.datetime.now(datetime.timezone.utc).isoformat()})
            user.emotion_history = hist[-100:] # Cap at 100
            await db.execute(update(User).where(User.id == user.id).values(emotion_history=user.emotion_history))

        return analysis, cache_hit

    def _apply_analysis_to_note(self, note: Note, analysis: Dict[str, Any]):
        note.title = analysis.get("title", "Untitled")
        note.summary = analysis.get("summary")
        note.action_items = analysis.get("action_items", [])
        note.tags = analysis.get("tags", [])
        note.mood = analysis.get("mood", "Neutral")
        # Handle clarification promotion
        ask = analysis.get("ask_clarification")
        if ask:
            if not note.action_items: note.action_items = []
            note.action_items.insert(0, f"Clarification Needed: {ask}")

analyze_core = AnalyzeCore()
