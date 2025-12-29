from .base import BaseIntegration
from app.models import Integration, Note
from app.core.http_client import http_client

class ZapierIntegration(BaseIntegration):
    async def sync(self, integration: Integration, note: Note):
        # AI Router Logic
        settings = integration.settings or {}
        routes = settings.get("routes", {})
        
        # Get metadata from ai_analysis field (JSONB)
        analysis = note.ai_analysis or {}
        intent = analysis.get("intent", "note")
        priority = analysis.get("priority", 4)
        suggested_project = analysis.get("suggested_project", "Inbox")

        # Determine target URL: specific intent route -> default route -> global webhook_url -> legacy access_token
        webhook_url = (
            routes.get(intent) or 
            routes.get("default") or 
            settings.get("webhook_url") or 
            integration.access_token # Fallback to access_token for backward compatibility
        )

        auto_trigger = settings.get("auto_trigger_new_note", True)

        if not auto_trigger:
             self.logger.info("Auto-trigger disabled for Zapier")
             return

        if not webhook_url or not isinstance(webhook_url, str) or not webhook_url.startswith("http"):
            self.logger.warning(f"Invalid or missing Zapier webhook URL for intent '{intent}'")
            return

        self.logger.info(f"Triggering Zapier AI Router (intent: {intent}) for user {note.user_id}")
        
        payload = {
            "event": "new_note",
            "note_id": note.id,
            "title": note.title,
            "summary": note.summary,
            "transcription": note.transcription_text,
            "tags": note.tags or [],
            "action_items": note.action_items or [],
            "intent": intent,
            "priority": priority,
            "suggested_project": suggested_project,
            "notion_properties": analysis.get("notion_properties", {}),
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "url": f"https://voicebrain.app/notes/{note.id}"
        }
        
        client = http_client.client
        await client.post(webhook_url, json=payload, timeout=10.0)
        self.logger.info(f"Zapier webhook sent to {webhook_url} (Intent: {intent})")
