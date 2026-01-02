from .base import BaseIntegration
from app.models import Integration, Note
from infrastructure.http_client import http_client
import logging

class CraftIntegration(BaseIntegration):
    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to Craft")
        
        # 1. Authenticate
        access_token = integration.auth_token
        if isinstance(access_token, dict):
            access_token = access_token.get("access_token") 
        
        if not access_token:
            raise ValueError("Craft API Token missing")
            
        space_id = (integration.settings or {}).get("space_id")
        # If space_id is missing, we might need to fetch available spaces and pick one,
        # but for this iteration we'll assume it's configured or fails.
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        client = http_client.client
        if not space_id:
            # Attempt to fetch primary space
            try:
                res = await client.get("https://docs.api.craft.do/auth/v1/profile", headers=headers)
                res.raise_for_status()
                # Profile endpoint usually returns default spaces or user info.
                # Actually Craft API auth/v1/profile returns spaces list.
                data = res.json()
                spaces = data.get("spaces", [])
                if spaces:
                    space_id = spaces[0]["id"]
                    self.logger.info(f"Using default Craft Space: {space_id}")
                else:
                    raise ValueError("No Craft Spaces found for user.")
            except Exception as e:
                raise ValueError(f"Failed to resolve Craft Space ID: {e}")

        # 2. Build Content Blocks
        blocks = []
        
        # Summary
        if note.summary:
            blocks.append({
                "type": "textBlock",
                "content": "Summary",
                "style": { "fontStyle": "bold" }
            })
            blocks.append({
                "type": "textBlock",
                "content": self.sanitize_text(note.summary)
            })
            blocks.append({"type": "textBlock", "content": ""}) # Spacer

        # Action Items
        if note.action_items:
            blocks.append({
                "type": "textBlock",
                "content": "Action Items",
                "style": { "fontStyle": "bold" }
            })
            for item in note.action_items:
                blocks.append({
                    "type": "textBlock",
                    "content": str(item),
                    "listStyle": { "type": "todo", "state": "unchecked" }
                })
            blocks.append({"type": "textBlock", "content": ""}) # Spacer

        # Transcript
        if note.transcription_text:
            blocks.append({
                "type": "textBlock",
                "content": "Transcript",
                "style": { "fontStyle": "bold" }
            })
             # Craft has character limits per block? Usually safe to split if massive, 
             # but for now we put it in one generic text block or code block.
             # Let's use simple text for readability.
            blocks.append({
                "type": "textBlock",
                "content": self.sanitize_text(note.transcription_text)[:10000] # Safety limit
            })
            blocks.append({"type": "textBlock", "content": ""})

        # Footer / Links
        base_url = "https://voicebrain.app"
        blocks.append({
            "type": "textBlock",
            "content": "Open in VoiceBrain",
            "link": { "url": f"{base_url}/dashboard/notes/{note.id}" }
        })

        # 3. Create Document
        # POST https://docs.api.craft.do/documents/v1/spaces/{spaceId}/documents
        
        body = {
            "content": [
                {
                    "type": "textBlock",
                    "content": self.sanitize_text(note.title or "Untitled Note"),
                    "style": { "textStyle": "title" } # Document title style
                },
                *blocks
            ]
            # Note: Craft API might handle the root block typically as the title if using create operations.
            # Actually, the 'create' endpoint usually takes a specific structure.
            # Let's try the standard structure: title + content blocks.
            # Checking API docs: Body: { folderId: "...", content: [ ... ] }
            # The first block in content usually becomes the title if not explicit? 
            # Actually, let's treat the first block as the title as per standard practice.
        }
        
        try:
            post_res = await client.post(
                f"https://docs.api.craft.do/documents/v1/spaces/{space_id}/documents",
                headers=headers,
                json=body
            )
            post_res.raise_for_status()
            self.logger.info("Successfully created Craft document.")
            
        except Exception as e:
            self.logger.error(f"Craft integration failed: {e}")
            raise e
