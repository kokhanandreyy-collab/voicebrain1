from typing import List, Optional, Dict, Any
import json
from loguru import logger

class PromptBuilder:
    """
    Constructs dynamic system and user prompts for note analysis.
    Handles context truncation and personalization.
    """
    
    DEFAULT_ANALYSIS_SCHEMA = (
        "Schema:\n"
        "1. 'title': Catchy title.\n"
        "2. 'summary': Markdown summary; remove audio/routing commands.\n"
        "3. 'action_items': List of strings; exclude 'send message' style commands.\n"
        "4. 'tags': 3-5 tags.\n"
        "5. 'mood': one of [positive, neutral, negative, frustrated]. Use emotion only for tone and empathy, not for intent or action decisions.\n"
        "6. 'calendar_events': [{title, date, time}].\n"
        "7. 'diarization': [{speaker, text}].\n"
        "8. 'intent': one of [task, event, note, crm, journal, idea].\n"
        "9. 'suggested_project': e.g. 'Work', 'Home'.\n"
        "10. 'priority': 1 (High) to 4 (Low).\n"
        "11. 'explicit_destination_app': e.g. 'todoist', 'slack' or null.\n"
        "12. 'adaptive_update': Dict of learned preferences or null.\n"
        "13. 'ask_clarification': Question if unsure about intent.\n"
        "14. 'empathetic_comment': 1 sentence based on mood.\n"
        "15. 'health_data', 'entities', 'notion_properties', 'identity_update', 'explicit_folder': as needed."
    )

    @classmethod
    def build_analysis_prompt(
        cls, 
        transcription: str, 
        user_context_str: str = "", 
        target_language: str = "Original",
        base_system_prompt: str = ""
    ) -> List[Dict[str, str]]:
        """Assembles the final messages list for the LLM."""
        
        # 1. Prepare Instructions
        lang_instr = ""
        if target_language and target_language != "Original":
            lang_instr = f"CRITICAL: Output title/summary/items in {target_language}."
            
        # 2. Build System Prompt
        system_content = (
            "You are VoiceBrain AI. Analyze the transcript and return ONLY a JSON object.\n"
            f"{user_context_str}\n"
            f"{lang_instr}\n\n"
            f"{base_system_prompt or cls.DEFAULT_ANALYSIS_SCHEMA}"
        )
        
        return [
            {"role": "system", "content": system_content.strip()},
            {"role": "user", "content": transcription}
        ]

    @classmethod
    def truncate_context(
        cls, 
        identity: str, 
        preferences: Dict[str, Any], 
        long_term: str, 
        recent_context: str
    ) -> str:
        """
        Ensures context stays under ~800 tokens (~3200 characters).
        Prioritization: Identity > Long-term (top 3) > Recent.
        """
        ctx_parts = []
        if identity: ctx_parts.append(f"User identity: {identity}")
        if preferences: ctx_parts.append(f"Adaptive preferences: {json.dumps(preferences, ensure_ascii=False)}")
        if long_term: ctx_parts.append(f"Long-term knowledge: {long_term}")
        if recent_context: ctx_parts.append(f"Recent context: {recent_context}")
        
        full_context = "\n".join(ctx_parts)
        est_tokens = len(full_context) // 4
        
        if est_tokens <= 800:
            return full_context
            
        logger.warning(f"Context overflow ({est_tokens} tokens). Truncating...")
        
        # Truncation Strategy
        pruned = []
        if identity: pruned.append(f"User identity: {identity}") # Always keep
        if preferences: pruned.append(f"Adaptive preferences: {json.dumps(preferences, ensure_ascii=False)}")
        if long_term: pruned.append(f"Long-term knowledge (Trimmed): {long_term[:1000]}")
        if recent_context: pruned.append(f"Recent context (Trimmed): {recent_context[:500]}")
        
        final_ctx = "\n".join(pruned)
        logger.info(f"Context truncated to ~{len(final_ctx)//4} tokens")
        return final_ctx
