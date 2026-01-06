import asyncio
import json
import hashlib
from typing import List, Optional, Dict, Any, Union
import redis.asyncio as redis
from loguru import logger
from openai import AsyncOpenAI
from sqlalchemy.future import select
import httpx

from infrastructure.config import settings
from app.core.types import AnalysisResult
from .llm_client import LLMClient
from .prompt_builder import PromptBuilder
from .response_parser import ResponseParser
from .cache_handler import CacheHandler

class AIService:
    """
    Orchestrator for all AI-related operations.
    Decomposed into specialized modules for scalability.
    """
    def __init__(self) -> None:
        self.redis = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        self.client = LLMClient(redis_client=self.redis)
        self.cache = CacheHandler(redis_client=self.redis)
        self.parser = ResponseParser()
        self.builder = PromptBuilder()

    async def transcribe_audio(self, audio_file_content: bytes) -> Dict[str, str]:
        """Transcribe audio using AssemblyAI API."""
        aai_key = settings.ASSEMBLYAI_API_KEY
        if not aai_key:
            logger.warning("ASSEMBLYAI_API_KEY not found. Using Mock.")
            await asyncio.sleep(1)
            return {"text": "Mock transcription: API Key missing."}

        headers = {"authorization": aai_key}
        from infrastructure.http_client import http_client
        try:
            # 1. Upload
            upload_res = await http_client.client.post("https://api.assemblyai.com/v2/upload", headers=headers, content=audio_file_content)
            upload_res.raise_for_status()
            upload_url = upload_res.json()["upload_url"]

            # 2. Start
            transcript_res = await http_client.client.post("https://api.assemblyai.com/v2/transcript", json={"audio_url": upload_url, "speaker_labels": True, "language_detection": True}, headers=headers)
            transcript_res.raise_for_status()
            transcript_id = transcript_res.json()["id"]

            # 3. Poll
            endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
            while True:
                poll_res = await http_client.client.get(endpoint, headers=headers)
                poll_data = poll_res.json()
                if poll_data["status"] == "completed": return {"text": poll_data["text"]}
                if poll_data["status"] == "error": raise RuntimeError(f"AssemblyAI Error: {poll_data.get('error')}")
                await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    async def get_system_prompt(self, key: str, default_text: str) -> str:
        """Fetches prompt from Redis or DB."""
        cache_key = f"system_prompt:{key}"
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached: return cached
        
        try:
            from infrastructure.database import AsyncSessionLocal
            from app.models import SystemPrompt
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(SystemPrompt).where(SystemPrompt.key == key))
                prompt = res.scalars().first()
                if prompt:
                    if self.redis: await self.redis.setex(cache_key, 300, prompt.text)
                    return prompt.text
        except Exception as e:
            logger.error(f"Error fetching system prompt: {e}")
        return default_text

    async def analyze_text(
        self, 
        text: str, 
        user_context: Optional[str] = None, 
        target_language: str = "Original",
        previous_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Main entry point for note analysis orchestration."""
        cached = await self.cache.get_analysis(text)
        if cached: return cached

        # Unified context
        full_ctx = "\n".join(filter(None, [user_context, previous_context]))
        # Fetch base prompt if exists
        base_prompt = await self.get_system_prompt("general_analysis", "")
        
        messages = self.builder.build_analysis_prompt(
            transcription=text,
            user_context_str=full_ctx,
            target_language=target_language,
            base_system_prompt=base_prompt
        )

        try:
            response = await self.client.get_completion(
                messages=messages, 
                model="deepseek-chat",
                response_format={"type": "json_object"}
            )
            result = self.parser.parse_analysis(response.choices[0].message.content)
            await self.cache.save_analysis(text, result)
            return result
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return self.parser.get_fallback_result(str(e))

    async def extract_health_metrics(self, text: str, user_id: Optional[str] = None, db: Any = None) -> Dict[str, Any]:
        """Specialized extraction for health data."""
        prev_health = "{}"
        if user_id and db:
            from app.models import Note
            res = await db.execute(select(Note).where(Note.user_id == user_id, Note.health_data != None).order_by(Note.created_at.desc()).limit(1))
            note = res.scalars().first()
            if note: prev_health = json.dumps(note.health_data)

        base_prompt = await self.get_system_prompt("extract_health", "Extract health metrics as JSON.")
        prompt = base_prompt.replace("{prev_health_json}", prev_health)
        
        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": text}]
        try:
            res = await self.client.get_completion(messages, model="deepseek-chat", response_format={"type": "json_object"})
            return json.loads(self.parser.clean_json(res.choices[0].message.content))
        except Exception: return {}

    async def generate_embedding(self, text: str) -> List[float]:
        """OpenAI-powered embeddings with caching."""
        cached = await self.cache.get_embedding(text)
        if cached: return cached
        try:
            res = await self.client.openai_client.embeddings.create(model="text-embedding-3-small", input=text)
            embedding = res.data[0].embedding
            await self.client._track_usage(res.usage)
            await self.cache.save_embedding(text, embedding)
            return embedding
        except Exception: return [0.0] * 1536

    async def ask_notes_stream(self, context: str, question: str, user_context: Optional[str] = None):
        """Streaming response for Ask AI."""
        system = f"User context: {user_context or ''}\nAnswer based on notes."
        user_msg = f"Context:\n{context}\n\nQuestion: {question}"
        
        client = self.client.deepseek_client or self.client.openai_client
        model = "deepseek-chat" if self.client.deepseek_client else "gpt-4o-mini"
        
        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
                stream=True,
                temperature=0.3
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Stream failed: {e}")
            yield "Error during streaming."

    async def ask_notes(self, context: str, question: str, user_context: Optional[str] = None) -> str:
        """Non-streaming Ask AI."""
        system = f"User context: {user_context or ''}\nAnswer based on notes."
        messages = [{"role": "system", "content": system}, {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}]
        res = await self.client.get_completion(messages, model="deepseek-chat")
        return res.choices[0].message.content

    async def analyze_weekly_notes(self, notes_context: str, target_language: str = "Original") -> str:
        """Generation of weekly coaching reports."""
        base = await self.get_system_prompt("weekly_review", "Analyze these notes for the week.")
        messages = [{"role": "system", "content": base}, {"role": "user", "content": notes_context}]
        res = await self.client.get_completion(messages, model="deepseek-chat")
        return res.choices[0].message.content

    async def get_chat_completion(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> str:
        res = await self.client.get_completion(messages, model=model or "gpt-4o")
        return res.choices[0].message.content

    async def get_embedding(self, text: str) -> List[float]:
        return await self.generate_embedding(text)

ai_service = AIService()
