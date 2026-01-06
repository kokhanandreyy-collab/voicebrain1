import json
import re
from typing import Dict, Any, Optional
from loguru import logger
from app.core.types import AnalysisResult

class ResponseParser:
    """
    Cleans, validates, and Repairs JSON responses from LLMs.
    """
    
    @staticmethod
    def clean_json(content: str) -> str:
        """Removes markdown blocks and artifacts to extract raw JSON."""
        if not content: return ""
        cleaned = content.strip()
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        return match.group(1) if match else cleaned

    @classmethod
    def parse_analysis(cls, content: str) -> Dict[str, Any]:
        """Parses and validates note analysis result."""
        raw_json = cls.clean_json(content)
        try:
            data = json.loads(raw_json)
            # Basic structural validation via Pydantic model
            AnalysisResult(**data)
            return data
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Response validation failed: {e}")
            raise ValueError(f"Invalid analysis structure: {str(e)}")

    @classmethod
    def get_fallback_result(cls, error_msg: str) -> Dict[str, Any]:
        """Provides a safe default object on total failure."""
        return AnalysisResult(
            title="Analysis Failure",
            summary=f"System error during analysis: {error_msg}",
            action_items=[],
            tags=["Error"],
            mood="Neutral"
        ).model_dump()
