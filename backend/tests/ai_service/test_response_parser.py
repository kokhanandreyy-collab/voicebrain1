import pytest
from app.services.ai_service.response_parser import ResponseParser

def test_clean_json_extraction():
    dirty = "Here is your JSON: ```json\n{\"title\": \"Test\"}\n``` Bye!"
    cleaned = ResponseParser.clean_json(dirty)
    assert cleaned == "{\"title\": \"Test\"}"

def test_parse_analysis_validation():
    valid = "{\"title\": \"A\", \"summary\": \"B\", \"action_items\": [], \"tags\": [], \"mood\": \"neutral\"}"
    result = ResponseParser.parse_analysis(valid)
    assert result["title"] == "A"
    
    with pytest.raises(ValueError):
        # Missing required fields like title or summary
        ResponseParser.parse_analysis("{}")
