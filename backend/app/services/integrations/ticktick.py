from .base import BaseIntegration
from app.models import Integration, Note
import httpx
import logging
from datetime import datetime
from dateutil import parser

class TickTickIntegration(BaseIntegration):
    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to TickTick")
        
        if not note.action_items:
            self.logger.info("No action items to sync.")
            return

        # 1. Authenticate
        access_token = integration.auth_token
        if isinstance(access_token, dict):
            access_token = access_token.get("access_token")
            
        if not access_token:
            raise ValueError("TickTick access token missing")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            # 2. Determine Due Date
            # Use the first calendar event date if available as a best-effort due date
            due_date_str = None
            if note.calendar_events and len(note.calendar_events) > 0:
                first_event = note.calendar_events[0]
                # calendar_events structure: { 'title': str, 'date': str (ISO or description), 'time': str }
                raw_date = first_event.get('date')
                if raw_date:
                    try:
                        # Attempt to parse
                        dt = parser.parse(raw_date)
                        # TickTick expects format: "2019-11-13T03:00:00+0000"
                        # Or just simple ISO. Open API says "dueDate": "yyyy-MM-dd'T'HH:mm:ssZ"
                        due_date_str = dt.strftime("%Y-%m-%dT%H:%M:%S%z")
                        if not due_date_str.endswith("Z") and "+" not in due_date_str and "-" not in due_date_str[-5:]:
                             # Add UTC if no timezone
                             due_date_str += "+0000"
                    except Exception as date_err:
                        self.logger.warning(f"Could not parse date for TickTick: {raw_date} - {date_err}")
                        due_date_str = None

            # 3. Create Tasks
            for item in note.action_items:
                try:
                    title_str = str(item)
                    safe_title = title_str[:250] if len(title_str) > 250 else title_str
                    
                    body = {
                        "title": safe_title,
                        "content": f"{note.summary or ''}\n\nVia VoiceBrain",
                        "tags": note.tags or [],
                        "priority": 3 if note.tags and "urgent" in [t.lower() for t in note.tags] else 0
                    }
                    
                    if due_date_str:
                        body["dueDate"] = due_date_str
                        
                    # Project ID could be in settings, defaults to Inbox if omitted
                    project_id = (integration.settings or {}).get("project_id")
                    if project_id:
                        body["projectId"] = project_id

                    post_res = await client.post(
                        "https://api.ticktick.com/open/v1/task",
                        headers=headers,
                        json=body
                    )
                    post_res.raise_for_status()
                    self.logger.info(f"Created TickTick task: {item[:20]}...")
                    
                except Exception as task_err:
                    self.logger.error(f"Failed to create TickTick task '{item}': {task_err}")
                    # Log but continue
