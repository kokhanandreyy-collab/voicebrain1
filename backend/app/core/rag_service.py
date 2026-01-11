from typing import List, Optional, Any
from loguru import logger
from sqlalchemy.future import select
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
import math
import datetime

from app.services.ai_service import ai_service
from app.models import Note, NoteEmbedding, LongTermMemory
from infrastructure.redis_client import short_term_memory
from infrastructure.config import settings

class RagService:
    def _calculate_temporal_score(self, importance: float, created_at: datetime.datetime) -> float:
        """
        Calculates a score based on importance and freshness.
        Score = importance * exp(-days_since_created / decay_constant)
        """
        if importance is None:
            importance = 5.0
            
        now = datetime.datetime.now(datetime.timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=datetime.timezone.utc)
            
        days_since = (now - created_at).total_seconds() / (24 * 3600)
        decay = settings.RAG_TEMPORAL_DECAY_DAYS or 30
        
        freshness_factor = math.exp(-days_since / decay)
        return importance * freshness_factor

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

    async def get_medium_term_context(self, user_id: str, note_id: str, text: str, db: AsyncSession) -> dict:
        """Fetch similar notes via Vector Search + Graph Relations (Medium-Term Memory)."""
        try:
            from app.models import NoteRelation
            
            # 1. Vector Search + Temporal Weighting
            query_vector = await ai_service.generate_embedding(text)
            # Fetch more candidates to re-rank by temporal score
            vector_res = await db.execute(
                select(Note)
                .join(NoteEmbedding)
                .where(Note.user_id == user_id, Note.id != note_id)
                .order_by(NoteEmbedding.embedding.cosine_distance(query_vector))
                .limit(20)
            )
            candidates = list(vector_res.scalars().all())
            
            # Re-rank by Temporal Score
            candidates.sort(
                key=lambda n: self._calculate_temporal_score(n.importance_score, n.created_at),
                reverse=True
            )
            vector_notes = candidates[:5]

            # 2. Graph Traversal (1-hop)
            vector_ids = set([n.id for n in vector_notes])
            graph_notes = []
            
            if vector_ids:
                graph_res = await db.execute(
                    select(NoteRelation)
                    .where(
                        (NoteRelation.note_id1.in_(vector_ids)) | 
                        (NoteRelation.note_id2.in_(vector_ids)),
                        NoteRelation.confidence > 0.6
                    )
                    .order_by(desc(NoteRelation.strength))
                )
                relations = graph_res.scalars().all()
                logger.info(f"Graph traversal: found {len(relations)} connections")
                
                neighbor_ids = []
                known_ids = vector_ids.copy()
                
                for r in relations:
                    if (r.strength or 0) <= 0.5:
                        continue
                    target = r.note_id2 if r.note_id1 in vector_ids else r.note_id1
                    if target not in known_ids:
                        neighbor_ids.append(target)
                        known_ids.add(target)
                        if len(neighbor_ids) >= 5:
                            break
                            
                if neighbor_ids:
                    nb_notes_res = await db.execute(select(Note).where(Note.id.in_(neighbor_ids)))
                    graph_notes = list(nb_notes_res.scalars().all())
            
            # Formatting
            v_parts = []
            for n in vector_notes:
                summary = n.summary[:200] if n.summary else (n.transcription_text[:200] if n.transcription_text else "No content")
                v_parts.append(f"Note: {n.title}\nSummary: {summary}")
            
            g_parts = []
            for n in graph_notes:
                summary = n.summary[:200] if n.summary else (n.transcription_text[:200] if n.transcription_text else "No content")
                g_parts.append(f"Related note: {summary}")

            return {
                "vector": "\n".join(v_parts) if v_parts else "No similar notes found.",
                "graph": "\n".join(g_parts) if g_parts else "No related graph connections found."
            }
        except Exception as e:
            logger.error(f"Medium-Term retrieval failed: {e}")
            return {"vector": "", "graph": ""}

    async def get_long_term_memory(self, user_id: str, db: AsyncSession, query_text: Optional[str] = None) -> str:
        """Fetch top long-term memories with temporal weighting."""
        try:
            if query_text:
                 query_vec = await ai_service.generate_embedding(query_text)
                 result = await db.execute(
                      select(LongTermMemory)
                      .where(LongTermMemory.user_id == user_id, LongTermMemory.is_archived == False, LongTermMemory.confidence > 0.6)
                      .order_by(LongTermMemory.embedding.cosine_distance(query_vec))
                      .limit(50)
                 )
                 candidates = list(result.scalars().all())
            else:
                   result = await db.execute(
                       select(LongTermMemory)
                       .where(LongTermMemory.user_id == user_id, LongTermMemory.is_archived == False, LongTermMemory.confidence > 0.6)
                       .order_by(desc(LongTermMemory.importance_score), desc(LongTermMemory.created_at))
                       .limit(20)
                   )
                   candidates = list(result.scalars().all())

            # Re-rank by Temporal Score
            candidates.sort(
                key=lambda x: self._calculate_temporal_score(x.importance_score, x.created_at),
                reverse=True
            )
            final = candidates[:5]

            parts = [f"- {s.summary_text} (Score: {s.importance_score})" for s in final]
            return "\n".join(parts) if parts else "No long-term knowledge recorded yet."
        except Exception as e:
            logger.error(f"Long-Term retrieval failed: {e}")
            return ""

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
            short_term = "\n".join([f"- {n.created_at.strftime('%Y-%m-%d')}: {n.summary[:100] if n.summary else n.transcription_text[:100]}" for n in st_notes])
        except Exception as e:
            logger.error(f"Short-term fetch failed: {e}")
            short_term = ""
            
        if not short_term: short_term = "No recent notes."

        # 2. Medium Term (RAG + Graph)
        mt_data = await self.get_medium_term_context(note.user_id, note.id, note.transcription_text, db)
        vector_context = mt_data["vector"]
        graph_context = mt_data["graph"]

        # 3. Long Term (Prioritized)
        long_term = await self.get_long_term_memory(note.user_id, db, query_text=note.transcription_text)
        if not long_term: long_term = "No long-term knowledge."

        return (
            f"Short-term context (Recent 10 notes):\n{short_term}\n\n"
            f"Recent context (Similar notes):\n{vector_context}\n\n"
            f"Graph connections:\n{graph_context}\n\n"
            f"Long-term knowledge (Key memories):\n{long_term}"
        )

    async def restore_memory(self, memory_id: str, db: AsyncSession) -> bool:
        """Restores an archived memory record."""
        result = await db.execute(select(LongTermMemory).where(LongTermMemory.id == memory_id))
        memory = result.scalars().first()
        if memory and memory.is_archived:
            memory.is_archived = False
            await db.commit()
            return True
        return False

rag_service = RagService()
