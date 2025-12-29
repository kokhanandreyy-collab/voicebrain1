from .base import BaseIntegration
from app.models import Integration, Note
from slack_sdk.web.async_client import AsyncWebClient
import logging

class SlackIntegration(BaseIntegration):
    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to Slack")
        
        # Initialize Client
        # Assumes access_token is a Bot User OAuth Token (xoxb-...)
        client = AsyncWebClient(token=integration.auth_token)
        
        # Determine Channel
        explicit_folder = (note.ai_analysis or {}).get("explicit_folder")
        channel_id = explicit_folder or (integration.settings or {}).get("target_channel_id")
        
        if not channel_id:
             self.logger.warning("No target_channel_id configured. Attempting to default to '#general'.")
             channel_id = "#general"

        # Construct Block Kit Message
        blocks = []
        
        # Header
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🎙️ New Note: {note.title or 'Untitled'}",
                "emoji": True
            }
        })
        
        # Summary
        if note.summary:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text":f"*Summary:*\n{note.summary}"
                }
            })
            
        # Action Items
        if note.action_items:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Action Items:*"
                }
            })
            # Checkbox elements are interactive and require more setup (interactivity URL).
            # For simple notification, a list is better.
            ai_text = ""
            for item in note.action_items:
                ai_text += f"• {item}\n"
                
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ai_text
                }
            })
            
        # Context / Link
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"<{f'https://voicebrain.app/notes/{note.id}'}|View Full Transcript & Audio>"
                }
            ]
        })

        for attempt in range(2):
            try:
                await client.chat_postMessage(
                    channel=channel_id,
                    text=f"New Note: {note.title}", # Fallback text
                    blocks=blocks
                )
                self.logger.info(f"Posted to Slack channel {channel_id}")
                return
            except Exception as e:
                # Catch 401/Unauthorized and try to refresh on first attempt
                if "invalid_auth" in str(e).lower() or "token_expired" in str(e).lower():
                    if attempt == 0:
                        self.logger.info("Slack token might be expired. Refreshing...")
                        # In Slack, if we have rotation, we handle it here.
                        # For now, let's assume ensure_token_valid is a placeholder
                        # or implemented if needed.
                        await self.ensure_token_valid(integration)
                        client = AsyncWebClient(token=integration.auth_token)
                        continue
                
                self.logger.error(f"Slack API error (Attempt {attempt+1}): {e}")
                if attempt == 1:
                    raise e
