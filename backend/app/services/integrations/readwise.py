from .base import BaseIntegration
from app.models import Integration, Note
from app.services.readwise_service import readwise_service

class ReadwiseIntegration(BaseIntegration):
    async def sync(self, integration: Integration, note: Note):
        # Check for auto_sync setting
        auto_sync = (integration.settings or {}).get("auto_sync", True)
        
        if not auto_sync:
            self.logger.info("Auto-sync disabled for Readwise")
            return

        # Prepare content with defaults and sanitization
        title = self.sanitize_text(note.title or "Voice Note")
        summary = self.sanitize_text(note.summary or "No summary available.")
        transcript = self.sanitize_text(note.transcription_text or "(No transcription available)")
        
        # Simple HTML construction
        html_content = f"<h1>{title}</h1>"
        html_content += f"<h2>Summary</h2><p>{summary}</p>" 
        html_content += f"<h2>Transcript</h2><p>{transcript}</p>"
        
        await readwise_service.save_to_reader(integration.auth_token, {
            "title": title,
            "url": f"https://voicebrain.app/notes/{note.id}",
            "html": html_content,
            "tags": note.tags,
            "author": "VoiceBrain"
        })
