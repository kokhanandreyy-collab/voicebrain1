from typing import Dict, Any, List, Optional
from loguru import logger
from sqlalchemy.future import select
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_service import ai_service
from app.models import Note, User, NoteEmbedding, LongTermSummary, NoteRelation
from app.core.types import AIAnalysisPack

class RagService:
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
    async def analyze_step(self, note: Note, user: Optional[User], db: AsyncSession, memory_service: Any) -> Dict[str, Any]:
        """
        Orchestrates the analysis: RAG Context -> AI Analysis -> Save
        """
        # 1. Context
        user_bio = user.bio if user else ""
        
        # Inject Identity Core
        if user and user.identity_summary:
            user_bio = f"{user_bio}\n\nUser Identity (Core Traits): {user.identity_summary}".strip()
            
        target_lang = user.target_language if user else "Original"
        
        hierarchical_context = await rag_service.build_hierarchical_context(note, db, memory_service)
        
        # 2. AI Analysis
        analysis = await ai_service.analyze_text(
            note.transcription_text,
            user_context=user_bio,
            target_language=target_lang,
            previous_context=hierarchical_context
        )
        
        # 3. Apply results
        self._apply_analysis_to_note(note, analysis)
        
        # 4. Embed
        await rag_service.embed_note(note, db)
        
        # 5. Short Term Memory
        await memory_service.add_action(note.user_id, {
            "type": "note_analyzed",
            "title": analysis.get("title"),
            "text": f"Analyzed: {analysis.get('title')}"
        })
        
        return analysis

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
            explicit_destination_app=analysis.get("explicit_destination_app"),
            explicit_folder=analysis.get("explicit_folder")
        )

analyze_core = AnalyzeCore()
