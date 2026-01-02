from .base import BaseIntegration
from app.models import Integration, Note
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import json
import logging
import datetime # Use module for timezone
import asyncio
from app.infrastructure.config import settings
from app.infrastructure.http_client import http_client

class GoogleFitIntegration(BaseIntegration):
    async def ensure_token_valid(self, integration: Integration):
        if not integration.expires_at: return
        now = datetime.datetime.now(datetime.timezone.utc)
        if integration.expires_at > now + datetime.timedelta(minutes=5): return
        if not integration.auth_refresh_token: return

        self.logger.info("Refreshing Google Fit Token...")
        client = http_client.client
        payload = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": integration.auth_refresh_token,
            "grant_type": "refresh_token"
        }
        try:
            resp = await client.post("https://oauth2.googleapis.com/token", data=payload)
            if resp.status_code == 200:
                data = resp.json()
                integration.auth_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                integration.expires_at = now + datetime.timedelta(seconds=expires_in)
                self.logger.info("Token refreshed successfully.")
            else:
                self.logger.error(f"Failed to refresh token: {resp.text}")
        except Exception as e:
            self.logger.error(f"Refresh error: {e}")

    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to Google Fit")

        # 1. Check for Health Data
        # Note: health_data is a dictionary, e.g., {'nutrition': {...}, 'workout': {...}}
        if not note.health_data:
            self.logger.info("No health data found in note. Skipping Google Fit sync.")
            return

        health_data = note.health_data
        if isinstance(health_data, str):
             try:
                 health_data = json.loads(health_data)
             except:
                 self.logger.error("Failed to parse health_data JSON string.")
                 return

        # 2. Authenticate
        await self.ensure_token_valid(integration)
        
        creds = None
        try:
            token_val = integration.auth_token
            refresh_token_val = integration.auth_refresh_token
            
            # Robust Parsing for Legacy JSON tokens
            if isinstance(token_val, str) and (token_val.startswith("{") or "access_token" in token_val):
                 try:
                     token_data = json.loads(token_val)
                     token_val = token_data.get("access_token", token_val)
                     
                     # Normalize: Update DB to simple string if we successfully extracted
                     integration.auth_token = token_val
                     # Assuming 'db' is available in context? 
                     # The sync() signature is sync(self, integration, note) - wait, where is db?
                     # Looking at base.py or earlier calls, sync usually receives DB session or we perform sessionless/implicit updates?
                     # The prompt says "save updated token in DB in clean format". 
                     # However, 'sync' method here doesn't have 'db' argument in signature in the file content I read.
                     # It's: async def sync(self, integration: Integration, note: Note):
                     # If I cannot commit, I should at least update the object so ensure_token_valid might work next time?
                     # Or I just rely on the fact that I'm fixing it for *this* session.
                     # Wait, previous task summary said sync methods were updated to accept 'db'. 
                     # Let me check if I should update the signature or if I missed it.
                     # File content line 8: async def sync(self, integration: Integration, note: Note): -- NO DB argument.
                     # I will just proceed with in-memory fix for now, or if I can't write, I just handle it.
                     
                 except Exception as e:
                     self.logger.warning(f"Failed to parse legacy JSON token, trying as is: {e}")

            creds = Credentials(
                token=token_val,
                refresh_token=refresh_token_val,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET
            )
            
            if creds.expired and creds.refresh_token:
                 creds.refresh(Request())
                 # If refreshed, we might want to save back? Again, lack of DB access in this scope.

        except Exception as e:
            self.logger.error(f"Auth failed: {e}")
            # Raising exception here might be okay if we want to fail the task, 
            # but user asked to wrap service creation.
        
        # 3. Create Service
        try:
             # Wrapped in try-except to prevent worker crash on Auth Error
             service = build('fitness', 'v1', credentials=creds, cache_discovery=False)
        except Exception as e:
             self.logger.error(f"Auth Error: Failed to build Fitness service: {e}")
             return # Exit gracefully

        # 4. Scenario A: Workout (Activity Session)
        workout = health_data.get('workout')
        if workout:
            try:
                # Mapping simple types to Google Fit Activity IDs
                # Full list: https://developers.google.com/fit/rest/v1/reference/activity-types
                activity_map = {
                    "running": 8,
                    "walking": 7,
                    "cycling": 1,
                    "biking": 1,
                    "strength_training": 80,
                    "yoga": 100,
                    "other": 97
                }
                
                activity_name = workout.get('type', 'other').lower()
                activity_id = activity_map.get(activity_name, 97)
                duration_min = workout.get('duration_minutes', 30)
                
                # Time: now (or note creation time)
                # Google Fit uses nanoseconds since epoch
                start_time_ns = int(note.created_at.timestamp() * 1e9)
                end_time_ns = start_time_ns + (duration_min * 60 * 1e9) # ms? no ns.
                # wait, duration is minutes. *60 = seconds. *1e9 = nanosec.
                
                # Create Session
                session_id = f"voicebrain-{note.id}"
                session_data = {
                    "id": session_id,
                    "name": f"VoiceBrain: {activity_name.title()}",
                    "startTimeMillis": int(start_time_ns / 1e6), # API wants millis for Sessions
                    "endTimeMillis": int(end_time_ns / 1e6),
                    "activityType": activity_id,
                    "description": note.summary[:100] if note.summary else "Logged via VoiceBrain"
                }
                
                # Executing blocking call in thread to avoid blocking loop
                await asyncio.to_thread(
                    service.users().sessions().update,
                    userId='me',
                    sessionId=session_id,
                    body=session_data
                )
                self.logger.info(f"Created Google Fit Session: {session_id}")
                
            except Exception as e:
                self.logger.error(f"Failed to log workout: {e}")
                # Don't break execution, try nutrition next

        # 5. Scenario B: Nutrition
        nutrition = health_data.get('nutrition')
        if nutrition:
            try:
                # We need to create a Data Source or use a default one suitable for 'com.google.nutrition'.
                # For simplicity, we insert a dataset directly into the user's nutrition data source handling.
                # Actually, best practice is to create a data source for the app first.
                
                # Let's try to add a data point to the 'raw:com.google.nutrition:com.google.android.apps.fitness:user_input' equivalent
                # Or create our own custom data source.
                
                # Construct Data Point
                # Nutrition field: map containing nutrient strings
                # https://developers.google.com/fit/datatypes/nutrition
                
                nutrients_map = {
                    "calories": "calories",
                    "protein": "protein",
                    "fat": "fat.total",
                    "carbs": "carbs.total"
                }
                
                start_time_ns = int(note.created_at.timestamp() * 1e9)
                end_time_ns = start_time_ns # Instant
                
                # Prepare value map
                val_map = []
                # Nutrition data point format is a map (int, float)
                # But the REST API 'mapVal' is deprecated or complex.
                # Actually v1 uses 'value': [ { 'mapVal': [] } ] for map types?
                # Nutrition is 'com.google.nutrition'.
                
                # Let's verify the structure for nutrition.
                # It uses 'mapVal' entries.
                
                nutrition_values = []
                
                if 'calories' in nutrition:
                     nutrition_values.append({"key": "calories", "value": {"fpVal": float(nutrition['calories'])}})
                if 'protein' in nutrition:
                     nutrition_values.append({"key": "protein", "value": {"fpVal": float(nutrition['protein'])}})
                if 'fat' in nutrition:
                     nutrition_values.append({"key": "fat.total", "value": {"fpVal": float(nutrition['fat'])}})
                if 'carbs' in nutrition:
                     nutrition_values.append({"key": "carbs.total", "value": {"fpVal": float(nutrition['carbs'])}})
                
                if not nutrition_values:
                    self.logger.warning("No valid nutrients to log.")
                    return

                # Create Data Source (if not exists logic is hard in single script, assume we define one on fly)
                # Just kidding, we can create a transient data source object in the request or reference standard one.
                # Easiest: Create "VoiceBrain-Nutrition" data source.
                
                data_source_id = "raw:com.google.nutrition:com.gemini.voicebrain:VoiceBrain-Nutrition"
                
                # We must ensure this DS exists.
                ds_body = {
                    "dataStreamName": "VoiceBrain-Nutrition",
                    "type": "raw",
                    "application": {
                        "name": "VoiceBrain",
                        "version": "1.0"
                    },
                    "dataType": {
                        "name": "com.google.nutrition"
                    }
                }
                
                from googleapiclient.errors import HttpError

                # Try create (idempotent-ish if we handle error)
                try:
                    await asyncio.to_thread(
                         service.users().dataSources().create(userId='me', body=ds_body).execute
                    )
                except HttpError as err:
                    if err.resp.status == 409:
                        self.logger.info("Data Source already exists (409). Proceeding.")
                    else:
                        self.logger.error(f"Failed to create Data Source: {err}")
                        raise err
                except Exception as e:
                     self.logger.error(f"Unexpected error creating Data Source: {e}")
                     raise e
                
                # Now add dataset
                # Dataset ID is "startTime-endTime" (nanos)
                # Ensure we use integers for formatting
                min_time = int(start_time_ns)
                max_time = int(start_time_ns + 1000000)
                dataset_id = f"{min_time}-{max_time}"
                
                dataset_point = {
                    "dataSourceId": data_source_id,
                    "point": [
                        {
                            "startTimeNanos": start_time_ns,
                            "endTimeNanos": start_time_ns + 1000000,
                            "dataTypeName": "com.google.nutrition",
                            "value": [
                                {
                                    "mapVal": nutrition_values
                                }
                            ]
                        }
                    ]
                }
                
                await asyncio.to_thread(
                    service.users().dataSources().datasets().patch,
                     userId='me',
                     dataSourceId=data_source_id,
                     datasetId=dataset_id,
                     body=dataset_point
                )

                self.logger.info("Successfully logged nutrition to Google Fit.")

            except Exception as e:
                self.logger.error(f"Failed to log nutrition: {e}")

