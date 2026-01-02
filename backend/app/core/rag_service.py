from typing import List, Optional
from loguru import logger
from sqlalchemy.future import select
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_service import ai_service
from app.models import Note, NoteEmbedding, LongTermSummary
from app.infrastructure.redis_client import short_term_memory

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
            # Find notes related to ANY of the user's top notes? Or just related to CURRENT note?
            # Current note might be new and have no relations yet.
            # RAG is used for analysis OF the current note.
            # So graph traversal isn't helpful for a *new* note which is not in the graph yet.
            # However, if we are analyzing a note that *was* in the graph or we use vector_notes to find *their* relations (2nd hop)?
            # "Traversal of graph + cosine".
            # Typically means: Vector search gives nodes -> Expand graph from those nodes.
            
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
            # Limit total to e.g. 10
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

rag_service = RagService()
