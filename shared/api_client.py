import httpx
import logging
from typing import Optional, Any, Dict, List
from .models import NoteResponse, AskResponse, IntegrationResponse

logger = logging.getLogger(__name__)

class VoiceBrainAPIClient:
    """
    Unified API Client for VoiceBrain backend.
    Used by Telegram Bot, CLI tools, and potentially other Python-based clients.
    """
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}{path}"
        headers = kwargs.get("headers", {})
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        kwargs["headers"] = headers
        
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"API Error ({e.response.status_code}): {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Connection Error: {e}")
            raise

    async def get_notes(self, limit: int = 10, skip: int = 0) -> List[Dict[str, Any]]:
        resp = await self._request("GET", "/notes", params={"limit": limit, "skip": skip})
        return resp.json()

    async def get_note_detail(self, note_id: str) -> Dict[str, Any]:
        resp = await self._request("GET", f"/notes/{note_id}")
        return resp.json()

    async def delete_note(self, note_id: str) -> bool:
        await self._request("DELETE", f"/notes/{note_id}")
        return True

    async def ask_ai(self, question: str) -> AskResponse:
        resp = await self._request("POST", "/notes/ask", json={"question": question})
        return AskResponse(**resp.json())

    async def upload_voice(self, files: Dict[str, Any]) -> Dict[str, Any]:
        resp = await self._request("POST", "/notes/upload", files=files)
        return resp.json()
    
    async def upload_text_note(self, text: str) -> Dict[str, Any]:
        # Utilizing the same /upload logic if backend supports JSON or multi-part text
        # Currently backend prefers files, but we can send transcription_text directly if supported
        resp = await self._request("POST", "/notes/upload", json={"transcription_text": text})
        return resp.json()

    async def reply_to_clarification(self, note_id: str, answer: str) -> Dict[str, Any]:
        resp = await self._request("POST", f"/notes/{note_id}/reply", json={"answer": answer})
        return resp.json()

    async def get_integrations(self) -> List[Dict[str, Any]]:
        resp = await self._request("GET", "/integrations")
        return resp.json()

    async def sync_note(self, note_id: str, provider: str) -> Dict[str, Any]:
        resp = await self._request("POST", f"/notes/{note_id}/share/{provider}")
        return resp.json()

    async def close(self):
        await self.client.aclose()
