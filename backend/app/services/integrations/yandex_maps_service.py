import httpx
from typing import Optional, Dict, Any
from loguru import logger
from sqlalchemy.future import select
from infrastructure.config import settings
from app.models import Integration, Note, NoteEmbedding
from app.services.ai_service import ai_service
from app.core.security import encrypt_token
from infrastructure.database import AsyncSessionLocal

class YandexMapsService:
    def __init__(self):
        self.api_key = settings.YANDEX_MAPS_API_KEY
        self.client_id = settings.YANDEX_OAUTH_CLIENT_ID
        self.client_secret = settings.YANDEX_OAUTH_CLIENT_SECRET
        self.geocoder_url = "https://geocode-maps.yandex.ru/1.x/"

    async def connect(self, user_id: str, code: str) -> str:
        """Exchange OAuth code for tokens and save."""
        token_url = "https://oauth.yandex.ru/token"
        
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data=payload)
            if resp.status_code != 200:
                logger.error(f"Yandex OAuth Failed: {resp.text}")
                raise Exception("Failed to connect Yandex Maps")
            
            data = resp.json()
            access_token = data.get("access_token")
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Integration).where(
                        Integration.user_id == user_id,
                        Integration.provider == "yandex_maps"
                    )
                )
                integration = result.scalars().first()
                
                if not integration:
                    integration = Integration(
                        user_id=user_id,
                        provider="yandex_maps",
                        access_token="legacy_token"
                    )
                    db.add(integration)
                
                integration.yandex_maps_access_token = encrypt_token(access_token)
                await db.commit()
                
            return "Connected"

    async def extract_location(self, text: str) -> Optional[str]:
        """Extract place/address using AI."""
        prompt = (
            "Identify the address, building, or place name in the following text. "
            "Return only the string of the most relevant location mentioned. "
            "If none, return 'None'."
        )
        result = await ai_service.ask_notes(text, prompt)
        if result.lower() == "none" or len(result) < 3:
            return None
        return result

    async def geocode_place(self, place_name: str) -> Optional[Dict[str, Any]]:
        """Geocode using Yandex Geocoder API."""
        params = {
            "apikey": self.api_key,
            "geocode": place_name,
            "format": "json",
            "results": 1
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.geocoder_url, params=params)
            data = resp.json()
            try:
                feature = data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
                coords = feature["Point"]["pos"].split() # "lon lat"
                return {
                    "address": feature["metaDataProperty"]["GeocoderMetaData"]["text"],
                    "coords": f"{coords[1]},{coords[0]}", # "lat,lon"
                    "name": feature["name"]
                }
            except (KeyError, IndexError):
                return None

    async def create_or_update_place(self, user_id: str, note_id: str, voice_text: str) -> str:
        """Process location and update note."""
        place_name = await self.extract_location(voice_text)
        if not place_name:
            return "No location detected"

        geo_data = await self.geocode_place(place_name)
        if not geo_data:
            return "Location not found in Yandex"

        lat_lon = geo_data["coords"]
        yandex_url = f"https://yandex.ru/maps/?ll={lat_lon.split(',')[1]}%2C{lat_lon.split(',')[0]}&text={geo_data['address'].replace(' ', '+')}&z=15"

        async with AsyncSessionLocal() as db:
            query_vector = await ai_service.generate_embedding(voice_text)
            
            # Simple RAG check for context (similar to Google flow)
            sim_result = await db.execute(
                select(Note)
                .join(NoteEmbedding)
                .where(Note.user_id == user_id, Note.id != note_id, Note.yandex_maps_url != None)
                .order_by(NoteEmbedding.embedding.cosine_distance(query_vector))
                .limit(3)
            )
            # Log similarity for context trace if needed
            
            note_result = await db.execute(select(Note).where(Note.id == note_id))
            note = note_result.scalars().first()
            if note:
                note.yandex_maps_url = yandex_url
                await db.commit()
                
        return yandex_url

    async def generate_route(self, start: str, end: str, avoid_traffic: bool = True) -> str:
        """Generate Yandex Maps route URL."""
        traffic = "1" if avoid_traffic else "0"
        return f"https://yandex.ru/maps/?rtext={start}~{end}&rtt=auto&trfm={traffic}"

yandex_maps_service = YandexMapsService()
