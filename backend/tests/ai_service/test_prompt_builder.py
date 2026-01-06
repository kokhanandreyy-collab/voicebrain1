import pytest
from app.services.ai_service.prompt_builder import PromptBuilder

def test_build_analysis_prompt_structure():
    messages = PromptBuilder.build_analysis_prompt(
        transcription="Hello",
        user_context_str="Dev",
        target_language="Russian"
    )
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "Dev" in messages[0]["content"]
    assert "Russian" in messages[0]["content"]
    assert messages[1]["content"] == "Hello"

def test_truncate_context_logic():
    identity = "Senior dev"
    prefs = {"theme": "dark"}
    # Large memories
    long_term = "Memory... " * 500 # ~2500 chars
    recent = "Recent... " * 500 # ~2500 chars
    
    truncated = PromptBuilder.truncate_context(identity, prefs, long_term, recent)
    
    assert "Senior dev" in truncated
    assert "dark" in truncated
    # Verify truncation (heuristic tokens length / 4)
    assert len(truncated) // 4 <= 850 # Small buffer allowed
