from .base import BaseIntegration
from app.models import Integration, Note
from notion_client import AsyncClient
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from notion_client.errors import APIResponseError
import logging
import datetime

class NotionIntegration(BaseIntegration):
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=(retry_if_exception_type((APIResponseError, ConnectionError, TimeoutError))),
        reraise=True
    )
    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to Notion (Context Aware)")
        
        notion = AsyncClient(auth=integration.auth_token)
        database_id = (integration.settings or {}).get("database_id")
        
        if not database_id:
             self.logger.warning("No database_id configured for Notion integration.")
             raise ValueError("Notion Database ID not configured. Please select a database in settings.")

        # 1. Extract AI Analysis Metadata
        analysis = note.ai_analysis or {}
        intent = analysis.get("intent", "note")
        suggested_project = analysis.get("suggested_project")
        entities = analysis.get("entities", [])
        ai_props = analysis.get("notion_properties", {})

        # 2. Search Before Create (Scenario A)
        existing_page_id = None
        search_filters = []
        
        explicit_folder = analysis.get("explicit_folder")
        
        if explicit_folder:
            search_filters.append({"property": "Name", "title": {"contains": explicit_folder}})
        if note.title:
            search_filters.append({"property": "Name", "title": {"equals": note.title}})
        if suggested_project:
            search_filters.append({"property": "Name", "title": {"equals": suggested_project}})
        
        for entity in entities[:5]: # Limit to avoid filter overload
            search_filters.append({"property": "Name", "title": {"contains": entity}})

        if search_filters:
            try:
                # Query the database
                search_res = await notion.databases.query(
                    database_id=database_id,
                    filter={"or": search_filters},
                    page_size=1
                )
                if search_res.get("results"):
                    existing_page_id = search_res["results"][0]["id"]
                    self.logger.info(f"Context match found: {existing_page_id}")
            except Exception as search_err:
                self.logger.warning(f"Notion context search failed: {search_err}")

        # 3. Prepare Blocks
        children = []
        
        # Context Marker (Divider + Header for appended entries)
        if existing_page_id:
             children.append({"object": "block", "type": "divider", "divider": {}})
             children.append({
                 "object": "block", 
                 "type": "heading_3", 
                 "heading_3": {
                     "rich_text": [{"type": "text", "text": {"content": f"New Entry: {note.created_at.strftime('%Y-%m-%d %H:%M') if note.created_at else 'Now'}"}}]
                 }
             })

        # Summary Block
        if note.summary:
            safe_summary = self.sanitize_text(note.summary)
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Summary"}}]
                }
            })
            # Split summary too if it happens to be > 2000
            summary_chunks = [safe_summary[i:i+2000] for i in range(0, len(safe_summary), 2000)]
            for chunk in summary_chunks:
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": chunk}}]
                    }
                })
            
        # Transcription Block
        if note.transcription_text:
             children.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Transcription"}}]}})
             safe_transcript = self.sanitize_text(note.transcription_text)
             text_chunks = [safe_transcript[i:i+2000] for i in range(0, len(safe_transcript), 2000)]
             for chunk in text_chunks:
                children.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}})

        # Action Items
        if note.action_items:
             children.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Action Items"}}]}})
             for item in note.action_items:
                 children.append({"object": "block", "type": "to_do", "to_do": {"rich_text": [{"type": "text", "text": {"content": str(item)}}], "checked": False}})

        # 4. Handle Scenario A vs B
        if existing_page_id:
            # Scenario A: Append to existing page
            try:
                await notion.blocks.children.append(
                    block_id=existing_page_id,
                    children=children
                )
                self.logger.info("Successfully appended blocks to existing Notion page.")
                return # Exit early
            except Exception as append_err:
                self.logger.error(f"Failed to append to existing page: {append_err}. Falling back to creation.")

        # Scenario B: Create New Page
        safe_title = self.sanitize_text(note.title or "Untitled Note")
        properties = {
            "Name": {"title": [{"text": {"content": safe_title[:2000]}}]}
        }
        
        if note.created_at:
             properties["Date"] = {"date": {"start": note.created_at.isoformat()}}

        if note.tags:
            properties["Tags"] = {"multi_select": [{"name": tag} for tag in note.tags]}

        # Map dynamic Notion Properties from AI Analysis
        for key, value in ai_props.items():
            if key in properties: continue
            try:
                # Heuristic mapping based on value type
                if isinstance(value, str):
                    if len(value) < 60:
                        properties[key] = {"select": {"name": value[:100]}}
                    else:
                        properties[key] = {"rich_text": [{"text": {"content": value[:2000]}}]}
                elif isinstance(value, (int, float)):
                    properties[key] = {"number": value}
                elif isinstance(value, list) and all(isinstance(v, str) for v in value):
                    properties[key] = {"multi_select": [{"name": str(v)[:100]} for v in value]}
            except Exception as e:
                self.logger.debug(f"Skipping dynamic property '{key}' due to mapping error: {e}")

        try:
            await notion.pages.create(
                parent={"database_id": database_id},
                properties=properties,
                children=children
            )
            self.logger.info("Successfully created new Notion page.")
        except Exception as e:
            self.logger.error(f"Notion Page Creation Error: {e}")
            raise e

