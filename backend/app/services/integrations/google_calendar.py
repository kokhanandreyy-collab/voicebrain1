from .base import BaseIntegration
from app.models import Integration, Note
from aiogoogle import Aiogoogle
from dateutil import parser
import datetime
import logging
from app.core.config import settings
from app.core.http_client import http_client

class GoogleCalendarIntegration(BaseIntegration):
    async def ensure_token_valid(self, integration: Integration, db):
        if not integration.expires_at:
             return
             
        # Check expiry (with 5 min buffer)
        now = datetime.datetime.now(datetime.timezone.utc)
        if integration.expires_at > now + datetime.timedelta(minutes=5):
            return

        if not integration.refresh_token:
            self.logger.warning("Token expired but no refresh token.")
            return

        self.logger.info("Refreshing Google Calendar Token...")
        client = http_client.client
        payload = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": integration.refresh_token,
            "grant_type": "refresh_token"
        }
        
        try:
            resp = await client.post("https://oauth2.googleapis.com/token", data=payload)
            if resp.status_code == 200:
                data = resp.json()
                integration.access_token = data["access_token"]
                # Update expiry
                expires_in = data.get("expires_in", 3600)
                integration.expires_at = now + datetime.timedelta(seconds=expires_in)
                
                # Save to DB
                db.add(integration)
                await db.commit()
                # Refresh to ensure session is clean (though it's same object)
                # await db.refresh(integration)
                
                self.logger.info("Token refreshed successfully.")
            else:
                self.logger.error(f"Failed to refresh token: {resp.text}")
        except Exception as e:
            self.logger.error(f"Refresh error: {e}")

    async def sync(self, integration: Integration, note: Note, db):
        # Pass db to ensure_token_valid
        await self.ensure_token_valid(integration, db)
        
        if not note.calendar_events:
            self.logger.info("No calendar events found to sync.")
            return

        self.logger.info(f"Syncing {len(note.calendar_events)} events to Google Calendar with conflict checks")
        
        user_creds = {
            "access_token": integration.access_token,
            "token_type": "Bearer", 
            "expires_in": 3600, 
        }

        async with Aiogoogle(user_creds=user_creds) as aiogoogle:
            calendar_v3 = await aiogoogle.discover('calendar', 'v3')
            
            for event_data in note.calendar_events:
                try:
                    title = event_data.get("title", f"VoiceBrain: {note.title[:30]}...")
                    date_val = event_data.get("date")
                    time_val = event_data.get("time")
                    
                    if not date_val:
                        self.logger.warning(f"Skipping event '{title}': Missing date.")
                        continue
                        
                    # 1. Parse Date and Time
                    try:
                        dt_input = f"{date_val} {time_val}" if time_val else date_val
                        dt = parser.parse(dt_input)
                        
                        # Timezone handling: Default to UTC if none specified
                        if dt.tzinfo is None:
                             dt = dt.replace(tzinfo=datetime.timezone.utc)
                        
                        start_iso = dt.isoformat()
                        # Default event duration: 1 hour
                        end_dt = dt + datetime.timedelta(hours=1)
                        end_iso = end_dt.isoformat()
                        
                    except Exception as date_err:
                        self.logger.warning(f"Date/Time parse error for '{date_val} {time_val}': {date_err}")
                        continue

                    # 2. Availability Check (Conflict Lookup)
                    conflicts = []
                    try:
                        # Fetch events in the same time window
                        # Added small buffer: 1 second
                        events_res = await aiogoogle.as_user(
                            calendar_v3.events.list(
                                calendarId='primary',
                                timeMin=start_iso,
                                timeMax=end_iso,
                                singleEvents=True
                            )
                        )
                        conflicts = events_res.get("items", [])
                    except Exception as list_err:
                        self.logger.warning(f"Failed to check calendar availability: {list_err}")

                    # 3. Handle Conflict
                    final_title = title
                    conflict_note = ""
                    
                    if conflicts:
                        self.logger.info(f"Conflict detected for '{title}': {len(conflicts)} overlap(s)")
                        final_title = f"[CONFLICT] {title}"
                        existing_titles = [e.get("summary", "Untitled Event") for e in conflicts]
                        conflict_note = f"\n⚠️ Warning: This event overlaps with: {', '.join(existing_titles)}\n"

                    # 4. Prepare Body
                    description = (
                        f"{conflict_note}\n"
                        f"🤖 AI Summary:\n{note.summary or 'No summary available.'}\n\n"
                        f"🔗 Link to Note: https://voicebrain.app/notes/{note.id}\n\n"
                        f"Original Transcription Snippet:\n{note.transcription_text[:500] if note.transcription_text else ''}..."
                    )

                    body = {
                        'summary': final_title,
                        'description': description,
                        'start': {'dateTime': start_iso},
                        'end': {'dateTime': end_iso},
                        'status': 'confirmed'
                    }
                    
                    # 5. Insert Event
                    await aiogoogle.as_user(calendar_v3.events.insert(
                        calendarId='primary',
                        json=body
                    ))
                    self.logger.info(f"Created event: {final_title}")

                except Exception as e:
                    self.logger.error(f"Failed to process calendar event '{title}': {e}")
                    # Don't raise here, allow other events in the loop to proceed
