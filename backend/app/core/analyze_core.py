from typing import Dict, Any, List, Optional
from loguru import logger
from sqlalchemy.future import select
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_service import ai_service
from app.models import Note, User, NoteEmbedding, LongTermMemory, NoteRelation
from app.core.types import AIAnalysisPack
from infrastructure.metrics import track_cache_hit, track_cache_miss

class RagService:
    """
    Manages the Retrieval-Augmented Generation (RAG) context construction.

    Implements a hierarchical memory lookup:
    1. Short-Term: Recent actions from Redis.
    2. Medium-Term: Vector Similarity (pgvector) + Note Graph (1-hop relations).
    3. Long-Term: Summarized high-importance memories from the `long_term_memory` table.
    """
    async def embed_note(self, note: Note, db: AsyncSession) -> None:
        """Generates embedding for the note and saves it."""
        text_content = f"{note.title} {note.summary} {note.transcription_text} {' '.join(note.tags)}"
        try:
            vector = await ai_service.generate_embedding(text_content)
            result = await db.execute(select(NoteEmbedding).where(NoteEmbedding.note_id == note.id))
            existing = result.scalars().first()
            if existing:
                existing.embedding = vector
            else:
                db.add(NoteEmbedding(note_id=note.id, embedding=vector))
        except Exception as e:
            logger.error(f"Embedding failed for note {note.id}: {e}")

    async def get_medium_term_context(self, user_id: str, note_id: str, text: str, db: AsyncSession) -> str:
        """Fetch top similar notes via Vector Search + Graph Relations (Medium-Term Memory)."""
        try:
            # 1. Vector Search
            query_vector = await ai_service.generate_embedding(text)
            vector_res = await db.execute(
                select(Note)
                .join(NoteEmbedding)
                .where(Note.user_id == user_id, Note.id != note_id)
                .order_by(NoteEmbedding.embedding.cosine_distance(query_vector))
                .limit(5)
            )
            vector_notes = list(vector_res.scalars().all())

            # 2. Graph Traversal (1-hop)
            related_ids = set([n.id for n in vector_notes])
            if related_ids:
                graph_res = await db.execute(
                    select(NoteRelation)
                    .where(
                        (NoteRelation.source_note_id.in_(related_ids)) | 
                        (NoteRelation.target_note_id.in_(related_ids))
                    )
                )
                relations = graph_res.scalars().all()
                for r in relations:
                    target = r.target_note_id if r.source_note_id in related_ids else r.source_note_id
                    related_ids.add(target)
            
            # Fetch content for extended graph
            final_ids = list(related_ids)[:10]
            if not final_ids:
                final_notes = []
            else:
                nb_res = await db.execute(select(Note).where(Note.id.in_(final_ids)))
                final_notes = nb_res.scalars().all()
            
            context_parts = []
            for n in final_notes:
                summary_part = n.summary[:200] if n.summary else "No summary"
                context_parts.append(f"Note: {n.title} (Related)\nSummary: {summary_part}")
            
            return "\n".join(context_parts) if context_parts else "No recent related context found."
        except Exception as e:
            logger.error(f"Medium-Term retrieval failed: {e}")
            return ""

    async def get_long_term_memory(self, user_id: str, db: AsyncSession) -> str:
        """Fetch top 3 high-importance long-term summaries."""
        try:
            result = await db.execute(
                select(LongTermMemory)
                .where(LongTermMemory.user_id == user_id, LongTermMemory.is_archived == False)
                .order_by(desc(LongTermMemory.importance_score))
                .limit(3)
            )
            summaries = list(result.scalars().all())
            parts = [f"- {s.summary_text}" for s in summaries]
            return "\n".join(parts) if parts else "No long-term knowledge recorded yet."
        except Exception as e:
            logger.error(f"Long-Term retrieval failed: {e}")
            return ""

    async def build_hierarchical_context(self, note: Note, db: AsyncSession, memory_service: Any) -> str:
        st_history = await memory_service.get_history(note.user_id)
        short_term_str = "\n".join([f"- {item.get('text', str(item))}" for item in st_history]) if st_history else "No recent history."
        medium_term_str = await self.get_medium_term_context(note.user_id, note.id, note.transcription_text, db)
        long_term_str = await self.get_long_term_memory(note.user_id, db)
        return (
            f"Short-term (Last actions):\n{short_term_str}\n\n"
            f"Recent context (Related notes):\n{medium_term_str}\n\n"
            f"Long-term knowledge (General themes):\n{long_term_str}"
        )

rag_service = RagService()

class AnalyzeCore:
    """
    Core Intelligence Engine for VoiceBrain.
    """
    async def analyze_note_by_id(self, note_id: str, db: AsyncSession, memory_service: Any) -> Dict[str, Any]:
        """
        Complete analysis orchestration from a note ID.
        Fetches note/user, checks cache, runs AI, and updates state.
        Used primarily by background workers and pipeline.
        """
        # 1. Fetch State
        res_note = await db.execute(select(Note).where(Note.id == note_id))
        note = res_note.scalars().first()
        if not note or not note.transcription_text:
            return {}

        res_user = await db.execute(select(User).where(User.id == note.user_id))
        user = res_user.scalars().first()

        # 2. Execute Analysis Logic
        analysis, _ = await self.analyze_step(note, user, db, memory_service)
        
        # 3. Finalize
        note.status = "analyzed"
        await db.commit()
        
        return analysis

    async def analyze_step(self, note: Note, user: Optional[User], db: AsyncSession, memory_service: Any) -> tuple[Dict[str, Any], bool]:
        """
        Orchestrates the analysis: RAG Context -> AI Analysis -> Save
        """
        # 1. Context
        user_bio = (user.bio or "") if user else ""
        
        # Inject Identity Core
        if user and user.identity_summary:
            user_bio = f"{user_bio}\n\nUser Identity (Core Traits): {user.identity_summary}".strip()
            
        # Inject Adaptive Preferences
        if user and user.adaptive_preferences:
            import json
            prefs_str = json.dumps(user.adaptive_preferences, indent=2)
            user_bio += f"\n\nAdaptive preferences: {prefs_str}"

        # Adaptive Learning Instruction
        user_bio += "\n\nAdaptive Learning: If you are unsure about the user's priority mapping (e.g. what 'high' means) or context, explicitly output a question in 'ask_clarification' field."
            
        target_lang = user.target_language if user else "Original"

        # Inject Emotion History (Task 1 & 3)
        if user and user.emotion_history:
            recent = user.emotion_history[-5:]
            emo_str = ", ".join([f"{e.get('mood')} ({e.get('date', 'anytime')})" for e in recent])
            user_bio += f"\n\nRecent Mood History: {emo_str}"
            last_mood = recent[-1].get('mood', 'neutral')
            user_bio += f"\nUser current mood: {last_mood}"
            user_bio += f"\nInstruction: Be empathetic to the user's current mood."
        
        hierarchical_context = await rag_service.build_hierarchical_context(note, db, memory_service)
        
        # Log Context Size for Monitoring
        logger.info(f"RAG Context Tokens (Est): {int(len(hierarchical_context)/4)} chars: {len(hierarchical_context)}")
        
        # 1.5 Semantic Cache Check (Task 3)
        from app.models import CachedAnalysis
        import datetime
        
        cache_hit = False
        cached_result = None
        current_embedding = None
        
        try:
            # Generate embedding for cache key
            current_embedding = await ai_service.generate_embedding(note.transcription_text)
            
            # Search cache
            # Cosine similarity > 0.9 approximately equals cosine distance < 0.1
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
                logger.info(f"Cache hit for note {note.id}")
                track_cache_hit("note_analysis")
                cached_result = cached_entry.result
                cache_hit = True
            else:
                logger.info(f"Cache miss for note {note.id}")
                track_cache_miss("note_analysis")
                
        except Exception as e:
            logger.warning(f"[Cache] Lookup failed: {e}")

        if cache_hit and cached_result:
            # Skip AI call
            analysis = cached_result
        else:
            # 2. AI Analysis
            analysis = await ai_service.analyze_text(
                note.transcription_text,
                user_context=user_bio,
                target_language=target_lang,
                previous_context=hierarchical_context
            )
            
            # Save to Cache
            try:
                if current_embedding:
                    ttl = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
                    new_cache = CachedAnalysis(
                        user_id=note.user_id,
                        embedding=current_embedding,
                        result=analysis,
                        expires_at=ttl
                    )
                    db.add(new_cache)
                    # We don't commit here immediately, usually the caller commits or we rely on session lifecycle.
                    # But analyze_step usually doesn't commit? Wait, pipeline commits.
                    # So adding to session is enough.
            except Exception as e:
                logger.warning(f"[Cache] Save failed: {e}")
        
        # 3. Apply results
        self._apply_analysis_to_note(note, analysis)

        # 3.0 Emotional Memory Update (Task 3)
        if user:
            new_mood = analysis.get("mood", "Neutral")
            history = list(user.emotion_history or [])
            history.append({
                "mood": new_mood,
                "date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "note_id": note.id
            })
            # Limit to last 20 entries
            user.emotion_history = history[-20:]
            from sqlalchemy import update
            await db.execute(update(User).where(User.id == user.id).values(emotion_history=user.emotion_history))
        
        # 3.1 Adaptive Learning: Process Identity Update
        identity_update = analysis.get("identity_update")
        if identity_update and user:
            logger.info(f"Adaptive Learning: Updating identity for user {user.id}")
            current_id = user.identity_summary or ""
            user.identity_summary = (current_id + f"\n- {identity_update}").strip()
            
        # 3.2 Adaptive Learning: Process Structured Preference Update
        adaptive_update = analysis.get("adaptive_update")
        if adaptive_update and isinstance(adaptive_update, dict) and user:
            logger.info(f"Adaptive Learning: Updating preferences for user {user.id}")
            current_prefs = dict(user.adaptive_preferences or {})
            current_prefs.update(adaptive_update)
            user.adaptive_preferences = current_prefs
            # Force update for JSON/SQLAlchemy
            from sqlalchemy import update
            await db.execute(update(User).where(User.id == user.id).values(adaptive_preferences=current_prefs))
            
        # 3.3 Clarifying Question Handling
        # If 'ask_clarification' exists, we put it in action_items so the user sees it immediately
        # Requirement: If DeepSeek response contains "not sure", "clarify", "don't know" in summary, we promote it
        ask_clarification = analysis.get("ask_clarification")
        
        # Phrase detection as requested
        summary_lower = str(analysis.get("summary", "")).lower()
        phrases = ["not sure", "не уверен", "уточни", "не знаю", "don't know", "clarify"]
        if not ask_clarification:
            for phrase in phrases:
                if phrase in summary_lower:
                    # Try to extract the sentence or just mark it
                    ask_clarification = "AI is unsure about some details. Please clarify."
                    break

        if ask_clarification:
            # Prepend to action items with distinct marker
            if not note.action_items: note.action_items = []
            note.action_items = [f"Clarification Needed: {ask_clarification}"] + list(note.action_items)
            # Ensure it is saved back
            note.action_items = list(note.action_items)
            # Record it in analysis dict too for frontend
            analysis["ask_clarification"] = ask_clarification
        
        # 4. Embed
        await rag_service.embed_note(note, db)
        
        # 5. Short Term Memory
        await memory_service.add_action(note.user_id, {
            "type": "note_analyzed",
            "title": analysis.get("title"),
            "text": f"Analyzed: {analysis.get('title')}"
        })
        
        return analysis, cache_hit

    def _apply_analysis_to_note(self, note: Note, analysis: Dict[str, Any]):
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
            empathetic_comment=analysis.get("empathetic_comment"),
            explicit_destination_app=analysis.get("explicit_destination_app"),
            explicit_folder=analysis.get("explicit_folder")
        )

analyze_core = AnalyzeCore()
