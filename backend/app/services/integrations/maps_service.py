import os
import httpx
from typing import Optional, Dict, Any
from loguru import logger
from sqlalchemy.future import select
from pathlib import Path

from app.infrastructure.config import settings
from app.models import Integration, Note, NoteEmbedding
from app.services.ai_service import ai_service
from app.core.security import encrypt_token, decrypt_token
from app.infrastructure.database import AsyncSessionLocal

class MapsService:
    async def create_or_update_place_2gis(self, user_id: str, note_id: str, voice_text: str) -> str:
        """Create or update a bookmark in 2GIS."""
        # 1. Extract Place Name/Context
        prompt = "Extract the name of the place mentioned in this text. Return ONLY the name."
        place_name = await ai_service.ask_notes(voice_text, prompt)
        
        async with AsyncSessionLocal() as db:
            # 2. Context Aware Search
            query_vector = await ai_service.generate_embedding(voice_text)
            sim_result = await db.execute(
                select(Note)
                .join(NoteEmbedding)
                .where(Note.user_id == user_id, Note.id != note_id, Note.twogis_url != None)
                .order_by(NoteEmbedding.embedding.cosine_distance(query_vector))
                .limit(1)
            )
            similar_note = sim_result.scalars().first()
            
            # 3. Mock 2GIS API Call
            twogis_url = f"https://2gis.ru/search/{place_name.replace(' ', '%20')}"
            
            note_res = await db.execute(select(Note).where(Note.id == note_id))
            note = note_res.scalars().first()
            if note:
                note.twogis_url = twogis_url
                await db.commit()
                
            return twogis_url

    async def create_or_update_place_mapsme(self, user_id: str, note_id: str, voice_text: str) -> str:
        """Add a bookmark to a local Maps.me KML file."""
        async with AsyncSessionLocal() as db:
            int_res = await db.execute(select(Integration).where(Integration.user_id == user_id, Integration.provider == "mapsme"))
            integration = int_res.scalars().first()
            if not integration or not integration.mapsme_path:
                return "Maps.me path not configured"
            
            file_path = decrypt_token(integration.mapsme_path)
            
            # Extract coordinates/name (Mock extraction)
            prompt = "Extract place name and approximate coordinates (lat, lon) from text if present. Return JSON: { 'name': str, 'lat': float, 'lon': float }"
            details_str = await ai_service.ask_notes(voice_text, prompt)
            try:
                import json
                details = json.loads(details_str.strip().replace("```json", "").replace("```", ""))
            except:
                details = {"name": f"Note_{note_id[:8]}", "lat": 0.0, "lon": 0.0}

            # Generate KML Placemark entry
            kml_entry = f"""
    <Placemark>
      <name>{details['name']}</name>
      <description>{voice_text}</description>
      <Point><coordinates>{details['lon']},{details['lat']}</coordinates></Point>
    </Placemark>
"""
            try:
                p = Path(file_path)
                os.makedirs(p.parent, exist_ok=True)
                
                content = ""
                if p.exists():
                    with open(p, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    if "</Document>" in content:
                        content = content.replace("</Document>", f"{kml_entry}\n</Document>")
                    else:
                        content += kml_entry
                else:
                    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>VoiceBrain Bookmarks</name>
{kml_entry}
  </Document>
</kml>"""

                with open(p, "w", encoding="utf-8") as f:
                    f.write(content)
                
                # Update Note
                note_res = await db.execute(select(Note).where(Note.id == note_id))
                note = note_res.scalars().first()
                if note:
                    note.mapsme_url = f"file://{file_path}"
                    await db.commit()
                    
                return str(file_path)
            except Exception as e:
                logger.error(f"Maps.me write error: {e}")
                return f"Error: {e}"

maps_service = MapsService()
