from typing import List, Optional, Any
from loguru import logger
from sqlalchemy.future import select
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_service import ai_service
from app.models import Note, NoteEmbedding, LongTermMemory
from infrastructure.redis_client import short_term_memory

class RagService:
    async def embed_note(self, note: Note, db: AsyncSession) -> None:
        """Generates embedding for the note and saves it."""
        text_content = f"{note.title} {note.summary} {note.transcription_text} {' '.join(note.tags)}"
        try:
            vector = await ai_service.generate_embedding(text_content)
            # Check existing
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
            from app.models import NoteRelation
            
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
                        (NoteRelation.note_id1.in_(related_ids)) | 
                        (NoteRelation.note_id2.in_(related_ids))
                    )
                )
                relations = graph_res.scalars().all()
                for r in relations:
                    # Traversal: if id1 is known, take id2, else id1
                    target = r.note_id2 if r.note_id1 in related_ids else r.note_id1
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

    async def get_long_term_memory(self, user_id: str, db: AsyncSession, query_text: Optional[str] = None) -> str:
        """Fetch top long-term memories. Prioritize high importance, then relevance + date."""
        try:
            if query_text:
                 query_vec = await ai_service.generate_embedding(query_text)
                 # Hybrid: Get 50 most similar (broad search)
                 result = await db.execute(
                     select(LongTermMemory)
                     .where(LongTermMemory.user_id == user_id)
                     .order_by(LongTermMemory.embedding.cosine_distance(query_vec))
                     .limit(50)
                 )
                 candidates = result.scalars().all()
                 # Strict Re-ranking: Priority = Score (desc) -> Date (desc)
                 candidates.sort(key=lambda x: (x.importance_score or 0, x.created_at), reverse=True)
                 final = candidates[:5]
            else:
                  result = await db.execute(
                      select(LongTermMemory)
                      .where(LongTermMemory.user_id == user_id)
                      .order_by(LongTermMemory.importance_score.desc(), LongTermMemory.created_at.desc())
                      .limit(5)
                  )
                 final = result.scalars().all()

            parts = [f"- {s.summary_text} (Score: {s.importance_score})" for s in final]
            return "\n".join(parts) if parts else "No long-term knowledge recorded yet."
        except Exception as e:
            logger.error(f"Long-Term retrieval failed: {e}")
            return ""

    async def build_hierarchical_context(self, note: Note, db: AsyncSession) -> str:
        """Aggregates Short, Medium, and Long term memory contexts."""
    async def build_hierarchical_context(self, note: Note, db: AsyncSession, memory_service: Any = None) -> str:
        """Aggregates Short, Medium, and Long term memory contexts."""
        # 1. Short Term (Last 10 Notes)
        try:
            st_res = await db.execute(
                select(Note)
                .where(Note.user_id == note.user_id, Note.id != note.id)
                .order_by(desc(Note.created_at))
                .limit(10)
            )
            st_notes = st_res.scalars().all()
            short_term = "\n".join([f"- {n.created_at.strftime('%Y-%m-%d')}: {n.summary[:100]}" for n in st_notes if n.summary])
        except Exception as e:
            logger.error(f"Short-term fetch failed: {e}")
            short_term = ""
            
        if not short_term: short_term = "No recent notes."

        # 2. Medium Term (RAG + Graph)
        medium_term = await self.get_medium_term_context(note.user_id, note.id, note.transcription_text, db)
        if not medium_term: medium_term = "No related notes found."

        # 3. Long Term (Top 3 Importance + Relevance)
        long_term = await self.get_long_term_memory(note.user_id, db, query_text=note.transcription_text)
        if not long_term: long_term = "No long-term knowledge."

        return (
            f"Short-term context (Recent 10 notes):\n{short_term}\n\n"
            f"Recent context (Similar notes):\n{medium_term}\n\n"
            f"Long-term knowledge (Key memories):\n{long_term}"
        )

rag_service = RagService()
