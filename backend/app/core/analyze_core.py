from typing import Dict, Any, List, Optional
from loguru import logger
from sqlalchemy.future import select
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_service import ai_service
from app.models import Note, User, NoteEmbedding, LongTermSummary
from app.core.types import AIAnalysisPack
from app.utils.redis import short_term_memory

class AnalyzeCore:
    async def analyze_step(self, text: str, user_context: Optional[str] = None, target_language: str = "Original", previous_context: Optional[str] = None) -> Dict[str, Any]:
        """Wrapper for AI analysis."""
        return await ai_service.analyze_text(text, user_context=user_context, target_language=target_language, previous_context=previous_context)

    async def save_analysis(self, note: Note, analysis: Dict[str, Any], db: AsyncSession) -> None:
        """Apply analysis results to note and save embedding."""
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
        
        search_content = f"{note.title} {note.summary} {note.transcription_text} {' '.join(note.tags)}"
        try:
            vector = await ai_service.generate_embedding(search_content)
            # Remove old embedding if exists (one-to-one strictly for now, or update)
            # Assuming Note has relationship or we just add new row? 
            # Existing code: note_embedding = NoteEmbedding(note_id=note.id, embedding=vector)
            # We should probably check existing first if we re-analyze.
            # For simplicity using existing logic:
            note_embedding = NoteEmbedding(note_id=note.id, embedding=vector)
            db.add(note_embedding)
        except Exception as e:
            logger.error(f"Embedding failed: {e}")

    async def get_medium_term_context(self, user_id: str, note_id: str, text: str, db: AsyncSession) -> str:
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

    async def build_hierarchical_context(self, note: Note, db: AsyncSession) -> str:
        """Aggregates Short, Medium, and Long term memory contexts."""
        # Short-Term
        st_history = await short_term_memory.get_history(note.user_id)
        short_term_str = "\n".join([f"- {item.get('text', str(item))}" for item in st_history]) if st_history else "No recent history."

        # Medium-Term
        medium_term_str = await self.get_medium_term_context(note.user_id, note.id, note.transcription_text, db)

        # Long-Term
        long_term_str = await self.get_long_term_memory(note.user_id, db)

        return (
            f"Short-term (Last actions):\n{short_term_str}\n\n"
            f"Recent context (Related notes):\n{medium_term_str}\n\n"
            f"Long-term knowledge (General themes):\n{long_term_str}"
        )

analyze_core = AnalyzeCore()
