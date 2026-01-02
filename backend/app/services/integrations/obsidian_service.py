import os
from pathlib import Path
from typing import Optional, List
from loguru import logger
from sqlalchemy.future import select

from app.models import Integration, Note, NoteEmbedding
from app.services.ai_service import ai_service
from app.core.security import encrypt_token, decrypt_token
from infrastructure.database import AsyncSessionLocal

class ObsidianService:
    async def connect(self, user_id: str, vault_path: str) -> str:
        """Store Obsidian vault path."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Integration).where(Integration.user_id == user_id, Integration.provider == "obsidian"))
            existing = result.scalars().first()
            if not existing:
                existing = Integration(user_id=user_id, provider="obsidian", access_token="local")
                db.add(existing)
            existing.obsidian_vault_path = encrypt_token(vault_path)
            await db.commit()
        return "Connected to Obsidian vault"

    async def create_or_update_note(self, user_id: str, note_id: str, voice_text: str) -> str:
        """Create or append to a markdown file in the Obsidian vault with smart backlinks."""
        async with AsyncSessionLocal() as db:
            # 1. Get Vault Path
            int_res = await db.execute(select(Integration).where(Integration.user_id == user_id, Integration.provider == "obsidian"))
            integration = int_res.scalars().first()
            if not integration or not integration.obsidian_vault_path:
                return "Obsidian not connected"
            
            vault_path = decrypt_token(integration.obsidian_vault_path)
            
            # 2. Extract Note Title/Content
            prompt = "Generate a short descriptive title for this note. Return ONLY the title."
            title = await ai_service.ask_notes(voice_text, prompt)
            safe_title = "".join([c for c in title if c.isalnum() or c in (" ", "-", "_")]).strip() or f"Note_{note_id[:8]}"
            
            # 3. Find Smart Backlinks using pgvector
            query_vector = await ai_service.generate_embedding(voice_text)
            sim_result = await db.execute(
                select(Note)
                .join(NoteEmbedding)
                .where(Note.user_id == user_id, Note.id != note_id)
                .order_by(NoteEmbedding.embedding.cosine_distance(query_vector))
                .limit(5)
            )
            similar_notes = sim_result.scalars().all()
            backlinks = "\n\n### Related Notes\n" + "\n".join([f"- [[{n.title or n.id[:8]}]]" for n in similar_notes if n.title])
            
            # 4. Write File
            file_name = f"{safe_title}.md"
            full_path = Path(vault_path) / file_name
            
            content = f"# {title}\n\n{voice_text}\n{backlinks}"
            
            try:
                # Ensure vault exists (mocking filesystem operations if in constrained env, but here we assume access)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "a" if full_path.exists() else "w", encoding="utf-8") as f:
                    if full_path.exists():
                        f.write(f"\n\n---\n*Updated {id[:8]}*\n{voice_text}\n")
                    else:
                        f.write(content)
                
                # Update Note record
                note_res = await db.execute(select(Note).where(Note.id == note_id))
                note = note_res.scalars().first()
                if note:
                    note.title = title
                    note.obsidian_note_path = str(full_path)
                    await db.commit()
                
                return str(full_path)
            except Exception as e:
                logger.error(f"Failed to write to Obsidian: {e}")
                return f"Error: {e}"

obsidian_service = ObsidianService()
