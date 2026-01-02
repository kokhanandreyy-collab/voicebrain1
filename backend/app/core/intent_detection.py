from typing import Dict, Any, List, Optional
from app.models import Note, User, AIAnalysisPack
from app.services.ai_service import ai_service
from app.core.rag_service import rag_service
from infrastructure.redis_client import short_term_memory
from app.core.types import AIAnalysisPack

class IntentDetectionService:
    async def analyze_note(self, note: Note, user: Optional[User], db) -> Dict[str, Any]:
        """
        Orchestrates the analysis:
        1. Context gathering (RAG + Memory)
        2. AI Analysis (Intent, Title, Summary, etc)
        3. Saving results
        """
        # 1. Context
        user_bio = user.bio if user else None
        target_lang = user.target_language if user else "Original"
        
        hierarchical_context = await rag_service.build_hierarchical_context(note, db)
        
        # 2. AI Analysis
        analysis = await ai_service.analyze_text(
            note.transcription_text,
            user_context=user_bio,
            target_language=target_lang,
            previous_context=hierarchical_context
        )
        
        # 3. Apply to Note
        self._apply_analysis_to_note(note, analysis)
        
        # 4. Save Embedding
        await rag_service.embed_note(note, db)
        
        # 5. Update Short Term Memory
        await short_term_memory.add_action(note.user_id, {
            "type": "note_analyzed",
            "title": analysis.get("title"),
            "text": f"Analyzed note: {analysis.get('title')}. Summary: {analysis.get('summary')[:100]}..."
        })
        
        return analysis

    def _apply_analysis_to_note(self, note: Note, analysis: Dict[str, Any]):
        note.title = analysis.get("title", "Untitled Note")
        note.summary = analysis.get("summary")
        note.action_items = analysis.get("action_items", [])
        note.calendar_events = analysis.get("calendar_events", [])
        note.tags = analysis.get("tags", [])
        note.diarization = analysis.get("diarization", [])
        note.mood = analysis.get("mood", "Neutral")
        note.health_data = analysis.get("health_data")
        
        note.ai_analysis = AIAnalysisPack(
            intent=analysis.get("intent", "note"),
            suggested_project=analysis.get("suggested_project", "Inbox"),
            entities=analysis.get("entities", []),
            priority=analysis.get("priority", 4),
            notion_properties=analysis.get("notion_properties", {}),
            explicit_destination_app=analysis.get("explicit_destination_app"),
            explicit_folder=analysis.get("explicit_folder")
        )

intent_service = IntentDetectionService()
