import asyncio
import os
import hashlib
import json
import redis.asyncio as redis
from openai import AsyncOpenAI
from app.core.config import settings
from sqlalchemy.future import select
from app.models import Note, User

class AIService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        # Redis Cache
        self.redis = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

    async def transcribe_audio(self, audio_file_content: bytes) -> dict:
        """
        Transcribe audio using AssemblyAI API.
        """
        import httpx
        
        aai_key = os.getenv("ASSEMBLYAI_API_KEY")
        
        if not aai_key:
            print("[WARN] ASSEMBLYAI_API_KEY not found. Using Mock Fallback.")
            await asyncio.sleep(2)
            return {"text": "Mock transcription (AssemblyAI): API Key missing."}

        headers = {
            "authorization": aai_key
        }

        async with httpx.AsyncClient() as client:
            try:
                # 1. Upload
                # AssemblyAI expects raw bytes in body
                print("Uploading audio to AssemblyAI...")
                upload_res = await client.post(
                    "https://api.assemblyai.com/v2/upload",
                    headers=headers,
                    content=audio_file_content
                )
                upload_res.raise_for_status()
                upload_url = upload_res.json()["upload_url"]

                # 2. Start Transcription
                print(f"Starting transcription for {upload_url}...")
                transcript_res = await client.post(
                    "https://api.assemblyai.com/v2/transcript",
                    json={
                        "audio_url": upload_url,
                        "speaker_labels": True, # For diarization
                        "language_detection": True # Auto-detect language
                    },
                    headers=headers
                )
                transcript_res.raise_for_status()
                transcript_id = transcript_res.json()["id"]

                # 3. Poll for Completion
                polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
                
                while True:
                    poll_res = await client.get(polling_endpoint, headers=headers)
                    poll_res.raise_for_status()
                    poll_data = poll_res.json()
                    
                    status = poll_data["status"]
                    if status == "completed":
                        return {"text": poll_data["text"]}
                    elif status == "error":
                        raise Exception(f"AssemblyAI Error: {poll_data['error']}")
                    
                    await asyncio.sleep(2) # Wait 2s before polling again
                    
            except Exception as e:
                print(f"AssemblyAI Transcription Error: {e}")
                raise e

    def clean_json_response(self, content: str) -> str:
        """
        Cleans LLM response by removing markdown and finding the outer JSON object.
        """
        if not content:
            return ""
        
        cleaned = content.strip()
        
        # 1. Regex to find outer {} ignoring markup
        import re
        # This matches the first '{' and the last '}', capturing everything in betweeen with DOTALL
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1)
            
        return cleaned

    async def get_system_prompt(self, key: str, default_text: str) -> str:
        """
        Fetches system prompt from Redis (cache) or DB.
        """
        cache_key = f"system_prompt:{key}"
        
        # 1. Check Redis
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                return cached
        
        # 2. Check DB
        try:
            from app.core.database import AsyncSessionLocal
            from app.models import SystemPrompt
            
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(SystemPrompt).where(SystemPrompt.key == key))
                prompt = result.scalars().first()
                
                if prompt:
                    text = prompt.text
                    # Cache for 5 minutes
                    if self.redis:
                        await self.redis.setex(cache_key, 300, text)
                    return text
        except Exception as e:
            print(f"Error fetching system prompt '{key}': {e}")
            
        return default_text

    async def analyze_text(self, text: str, user_context: str = None, target_language: str = "Original") -> dict:
        """
        Analyze text using DeepSeek V3 (via OpenAI-compatible API).
        """
        # Configure Analysis Client (DeepSeek > OpenAI > Mock)
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        deepseek_base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        
        analysis_client = None
        analysis_model = "gpt-4o"

        if deepseek_key:
            analysis_client = AsyncOpenAI(api_key=deepseek_key, base_url=deepseek_base)
            analysis_model = "deepseek-chat"
        elif self.client:
            analysis_client = self.client
            analysis_model = "gpt-4o"

        if not analysis_client:
            await asyncio.sleep(1)
            return {
                "title": "Mock Analysis (No Keys)",
                "summary": "Please set DEEPSEEK_API_KEY or OPENAI_API_KEY to enable AI analysis.",
                "action_items": ["Add API Keys"],
                "calendar_events": [],
                "tags": ["Mock", "Config Required"],
                "mood": "Waiting"
            }

        try:
            # System Prompt for DeepSeek
            # We add specific place in prompt for User Context
            context_instruction = f"\nUSER CONTEXT (Bio/Jargon): {user_context}\nUse this context to correctly identify names, projects, and specific jargon." if user_context else ""
            
            # Language Instruction
            lang_instruction = ""
            if target_language and target_language != "Original":
                lang_instruction = f"\nCRITICAL: Regardless of the input language, ALWAYS generate the Title, Summary, and Action Items in {target_language} language."

            default_prompt = (
                "You are an advanced AI assistant powered by DeepSeek V3. "
                "Analyze the user's audio transcription. "
                f"{context_instruction}"
                f"{lang_instruction}"
                "Return a valid JSON object with the following fields:\n"
                "1. 'title': A short, catchy, creative title.\n"
                "2. 'summary': A markdown formatted summary with bullet points and sections.\n"
                "3. 'action_items': A list of actionable tasks (strings), e.g., ['Buy milk', 'Email John']. Empty if none.\n"
                "4. 'tags': A list of 3-7 automatic tags.\n"
                "5. 'mood': One word describing the mood.\n"
                "6. 'calendar_events': A list of objects { 'title': str, 'date': str (ISO or description), 'time': str } if any dates/times are mentioned. Empty list if none.\n"
                "7. 'diarization': A list of objects { 'speaker': str, 'text': str } representing the conversation flow.\n"
                "8. 'health_data': A structured object for Apple Health export. If relevant data is found, return { 'nutrition': { 'calories': int, 'protein': int, 'carbs': int, 'fat': int, 'water_ml': int, 'name': str }, 'workout': { 'type': str, 'duration_minutes': int, 'calories_burned': int }, 'symptoms': [str] }. If no health data, return null.\n"
                "9. 'intent': Classify the primary intent into one of: ['task', 'event', 'note', 'crm', 'journal', 'shopping', 'idea'].\n"
                "10. 'suggested_project': Guess the project context (e.g., 'Work', 'Home', 'Startup', 'Health', 'Travel').\n"
                "11. 'entities': A list of strings (people, places, specific companies/products mentioned) for linking.\n"
                "12. 'priority': Integer from 1 (High/Urgent) to 4 (Low/Someday).\n"
                "13. 'notion_properties': A JSON object guessing properties for a Notion database entry (e.g. {'Status': 'In Progress', 'Category': 'Research'}).\n"
                "14. 'explicit_destination_app': Detect if the user explicitly specifies a destination in the voice command. One of ['todoist', 'notion', 'slack', 'google_calendar', 'google_drive', 'dropbox', 'email'] or null if none mentioned.\n"
                "15. 'explicit_folder': Extract the specific folder, project, or database name mentioned (e.g., 'Work', 'Journal', 'Home') or null.\n\n"
                "CRITICAL: The 'summary' and 'action_items' fields must NOT contain the routing command itself (e.g., 'send this to Todoist', 'put this in my work project'). Clean the text by removing these instructions."
            )
            
            # If the prompt text in DB has {user_context}, we can format it. 
            # If not, we rely on the default logic above inserting it.
            # But get_system_prompt returns raw text.
            # If the user edited the prompt in Admin Panel, they might not have {user_context}.
            # So we should probably append it to the message list if possible, or append to system prompt text.
            
            base_system_prompt = await self.get_system_prompt("general_analysis", default_prompt)
            
            # If the fetched prompt doesn't look like it has context logic, we append it.
            if user_context and "USER CONTEXT" not in base_system_prompt:
                 base_system_prompt += f"\n\nUSER CONTEXT: {user_context}"
            
            # If not present already, append language instruction
            if lang_instruction and "ALWAYS generate the Title" not in base_system_prompt:
                 base_system_prompt += f"\n{lang_instruction}"
            
            system_prompt = base_system_prompt

            # Check Cache
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            cache_key = f"cache:ai:analysis:{text_hash}"
            if self.redis:
                cached = await self.redis.get(cache_key)
                if cached:
                    return json.loads(cached)

            response = await analysis_client.chat.completions.create(
                model=analysis_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                response_format={ "type": "json_object" }
            )
            content = response.choices[0].message.content
            
            # Clean and Parse JSON
            cleaned_content = self.clean_json_response(content)
            try:
                result = json.loads(cleaned_content)
            except json.JSONDecodeError as decode_err:
                print(f"JSON Decode Error: {decode_err}. Attempting REPAIR.")
                try:
                    # Retry with repair instructions
                    repair_prompt = (
                        "The previous response was invalid JSON. "
                        "Please regenerate the exact same analysis but ensure it is strictly valid JSON. "
                        "Do not include markdown blocks or extra text."
                    )
                    retry_res = await analysis_client.chat.completions.create(
                        model=analysis_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text},
                            {"role": "assistant", "content": content},
                            {"role": "user", "content": repair_prompt}
                        ],
                        response_format={ "type": "json_object" }
                    )
                    retry_content = self.clean_json_response(retry_res.choices[0].message.content)
                    result = json.loads(retry_content)
                    print("JSON Repair Successful.")
                    
                except Exception as retry_e:
                    print(f"JSON Repair Failed: {retry_e}")
                    # Fallback Structure
                    return {
                        "status": "analysis_failed",
                        "title": "Analysis Error",
                        "summary": f"Failed to parse AI response: {str(decode_err)}",
                        "action_items": [],
                        "tags": ["Error", "Parse Fail"],
                        "mood": "Error",
                        "calendar_events": [],
                        "diarization": [],
                        "health_data": None
                    }
            
            # Cache Result
            if self.redis:
                await self.redis.setex(cache_key, 604800, json.dumps(result))
                
            return result
        except Exception as e:
            print(f"DeepSeek Analysis Error: {e}")
            return {
                "status": "analysis_failed",
                "title": "Analysis Failed",
                "summary": "An error occurred while analyzing the audio.",
                "action_items": [],
                "tags": ["Error"],
                "mood": "Error",
                "calendar_events": [],
                "diarization": [],
                "health_data": None
            }

    async def extract_health_metrics(self, text: str, user_id: str = None, db=None) -> dict:
        """
        Extracts health-related metrics and provides trend compliments.
        """
        # 1. Fetch Previous Health Data (Context Lookup)
        prev_health_json = "{}"
        if user_id and db:
            try:
                # Find most recent previous note with health data
                result = await db.execute(
                    select(Note).where(
                        Note.user_id == user_id,
                        Note.health_data != None,
                        Note.health_data != {}
                    ).order_by(Note.created_at.desc()).limit(1)
                )
                prev_note = result.scalars().first()
                if prev_note and prev_note.health_data:
                    prev_health_json = json.dumps(prev_note.health_data)
                    print(f"Found historical health context for user {user_id}")
            except Exception as e:
                print(f"Error fetching historical health data: {e}")

        # 2. Setup AI Client
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        deepseek_base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        
        analysis_client = None
        if deepseek_key:
            analysis_client = AsyncOpenAI(api_key=deepseek_key, base_url=deepseek_base)
        elif self.client:
            analysis_client = self.client

        if not analysis_client:
            return {"status": "mock", "message": "API Key not set"}
            
        default_prompt = (
            "You are a Health Data Assistant. Analyze the text for health and fitness metrics. "
            "Extract specific values like 'Steps', 'Weight', 'Sleep Duration', 'Distance Ran', 'Water Intake', 'Heart Rate'. "
            "Return a JSON object where keys are metric names (e.g., 'Weight', 'Steps') and values are strings with units (e.g., '75 kg', '8500 steps'). "
            "\n\n"
            f"Compare with previous data: {prev_health_json}. "
            "If there is a positive trend (e.g. weight drop, run distance increased, more water), "
            "add a field 'trend_compliment': 'Keep it up! Down 2kg since last time.' or similar. "
            "Ensure the output is strictly valid JSON."
        )
        
        system_prompt = await self.get_system_prompt("extract_health", default_prompt)
        
        # Inject dynamic context if prompt still contains placeholder (optional enhancement)
        # But here the placeholder {prev_health_json} was in the template. 
        # If we load from DB, the DB text might contain {prev_health_json}.
        # So we should format it.
        try:
             system_prompt = system_prompt.format(prev_health_json=prev_health_json)
        except:
             pass # Ignore formatting errors if keys missing

        try:
            response = await analysis_client.chat.completions.create(
                 model="deepseek-chat" if deepseek_key else "gpt-4o",
                 messages=[
                     {"role": "system", "content": system_prompt},
                     {"role": "user", "content": text}
                 ],
                 response_format={ "type": "json_object" }
            )
            content = response.choices[0].message.content
            cleaned_content = self.clean_json_response(content)
            try:
                return json.loads(cleaned_content)
            except json.JSONDecodeError:
                print(f"JSON Decode Error in extract_health_metrics. Raw content: {content}")
                return {}
        except Exception as e:
            print(f"Health Extraction Error: {e}")
            return {}


    async def generate_embedding(self, text: str) -> list:
        """
        Generate vector embedding for semantic search using OpenAI.
        """
        if not self.client:
            # Mock embedding (1536 dims)
            return [0.0] * 1536

        try:
            # Check Cache
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            cache_key = f"cache:ai:embedding:{text_hash}"
            if self.redis:
                cached = await self.redis.get(cache_key)
                if cached:
                    return json.loads(cached)

            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            embedding = response.data[0].embedding
            
            # Cache Result
            if self.redis:
                await self.redis.setex(cache_key, 604800, json.dumps(embedding))
            
            return embedding
        except Exception as e:
            print(f"Embedding Error: {e}")
            return [0.0] * 1536

    async def ask_notes(self, context: str, question: str) -> str:
        """
        Answer a user question based on the provided note context.
        """
        if not self.client:
            await asyncio.sleep(1)
            return "Reference Answer: This is a mock response because OPENAI_API_KEY is not set. Context was: " + context[:50] + "..."

        try:
            default_prompt = (
                "You are VoiceBrain, a helpful AI assistant. "
                "Answer the user's question using ONLY the provided context from their notes. "
                "If the answer is not in the context, say 'I couldn't find that information in your notes.' "
                "Keep answers concise and friendly.\n"
                "At the end of the answer, strictly list the titles of the notes you used as sources in a section titled '**Sources:**'."
            )
            
            system_prompt = await self.get_system_prompt("ask_notes", default_prompt)
            
            user_content = f"Context:\n{context}\n\nQuestion: {question}"

            # Use DeepSeek if available, else gpt-4o-mini (cost effective)
            deepseek_key = os.getenv("DEEPSEEK_API_KEY")
            if deepseek_key:
                client = AsyncOpenAI(api_key=deepseek_key, base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
                model = "deepseek-chat"
            else:
                client = self.client
                model = "gpt-4o-mini"

            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.3, # Lower temperature for factual answers
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Ask AI Error: {e}")
            return "Sorry, I encountered an error while analyzing your notes."

    async def analyze_weekly_notes(self, notes_context: str, target_language: str = "Original") -> str:
        """
        Generates a coaching-style weekly review based on note summaries.
        """
        if not self.client:
            return "Mock Weekly Review: Great week! You focused on X. Mood was mostly positive."

        try:
            lang_instruction = ""
            if target_language and target_language != "Original":
                lang_instruction = f" CRITICAL: Write the entire review in {target_language} language."

            default_prompt = (
                "You are VoiceBrain Coach. "
                "Analyze the user's notes from the past week. "
                "Identify: 1. Main focus area. 2. Dominant mood pattern. 3. Procrastinated items (mentioned multiple times but seemingly not done, if any). "
                "Write a helpful, encouraging, coaching-style summary (approx 200 words). "
                "Format with Markdown (## Focus, ## Mood, ## Suggestions)."
                f"{lang_instruction}"
            )
            
            system_prompt = await self.get_system_prompt("weekly_review", default_prompt)
            if lang_instruction and "Write the entire review in" not in system_prompt:
                system_prompt += f"\n{lang_instruction}"
            
            # Use DeepSeek or GPT-4o-mini
            deepseek_key = os.getenv("DEEPSEEK_API_KEY")
            if deepseek_key:
                client = AsyncOpenAI(api_key=deepseek_key, base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
                model = "deepseek-chat"
            else:
                client = self.client
                model = "gpt-4o-mini"

            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Notes from last 7 days:\n{notes_context}"}
                ],
                temperature=0.7,
                max_tokens=600
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Weekly Review Error: {e}")
            return "Could not generate weekly review due to an error."

ai_service = AIService()
