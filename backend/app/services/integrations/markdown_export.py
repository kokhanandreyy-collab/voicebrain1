from .base import BaseIntegration
from app.models import Integration, Note
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType, UploadFile
from app.core.config import settings
from starlette.datastructures import UploadFile as StarletteUploadFile
import logging
import tempfile
import os
import aiofiles

class EmailExportIntegration(BaseIntegration):
    def _auto_link_entities(self, text: str, entities: list[str]) -> str:
        """Wraps known entities in Obsidian-style [[ ]] brackets."""
        if not text or not entities:
            return text
        
        import re
        # Sort entities by length descending to match longer phrases first
        for entity in sorted(entities, key=len, reverse=True):
            # Case insensitive match with word boundaries
            pattern = re.compile(rf'\b({re.escape(entity)})\b', re.IGNORECASE)
            text = pattern.sub(r'[[\1]]', text)
        return text

    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to Email Backup")
        
        recipient = None
        try:
             recipient = integration.user.email
        except:
             self.logger.error("User relationship not loaded.")
             raise Exception("User not loaded")

        if not recipient:
             raise Exception("User has no email address")

        # 1. Extract Agentic Metadata
        analysis = note.ai_analysis or {}
        entities = analysis.get("entities", [])
        
        # 2. Format content
        tags_str = f"[{', '.join(note.tags)}]" if note.tags else "[]"
        entities_str = f"[{', '.join([f'\"{e}\"' for e in entities])}]" if entities else "[]"
        date_str = note.created_at.strftime('%Y-%m-%d') if note.created_at else ""
        
        # Apply Auto-Linking
        linked_summary = self._auto_link_entities(note.summary or "", entities)
        linked_transcript = self._auto_link_entities(note.transcription_text or "", entities)

        md_content = f"""---
tags: {tags_str}
entities: {entities_str}
date: {date_str}
voicebrain_id: {note.id}
---
# {note.title or 'Untitled'}

## Summary
{linked_summary}

## Action Items
"""
        if note.action_items:
            for item in note.action_items:
                md_content += f"- [ ] {item}\n"
        
        md_content += f"""
## Transcript
{linked_transcript}
"""
        
        # 2. Create Temp File
        # fastapi-mail requires a path or list of UploadFile.
        # Generating a temp file is safest.
        
        safe_title = "".join([c for c in (note.title or "untitled") if c.isalnum() or c in (' ', '-', '_')]).strip()
        filename = f"{safe_title}.md"
        
        tmp_path = None
        
        try:
            # Create a temp file
            # We use delete=False so we can close it and let fastapi-mail read it, then delete later.
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".md", encoding='utf-8') as tmp:
                tmp.write(md_content)
                tmp_path = tmp.name
            
            # 3. Configure Email
            conf = ConnectionConfig(
                MAIL_USERNAME=settings.SMTP_USER,
                MAIL_PASSWORD=settings.SMTP_PASSWORD,
                MAIL_FROM=settings.SMTP_FROM,
                MAIL_PORT=settings.SMTP_PORT,
                MAIL_SERVER=settings.SMTP_HOST,
                MAIL_STARTTLS=True,
                MAIL_SSL_TLS=False,
                USE_CREDENTIALS=True,
                VALIDATE_CERTS=True
            )

            message = MessageSchema(
                subject=f"VoiceBrain Backup: {filename}",
                recipients=[recipient],
                body=f"Attached is your markdown export for '{note.title}'.",
                subtype=MessageType.plain,
                attachments=[tmp_path]
            )

            fm = FastMail(conf)
            await fm.send_message(message)
            self.logger.info(f"Backup email sent to {recipient}")
            
        except Exception as e:
            self.logger.error(f"Email export failed: {e}")
            raise e
            
        finally:
            # Cleanup
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass
