from typing import List, Optional, TypedDict, Any
from pydantic import BaseModel, Field

class AnalysisResult(BaseModel):
    title: str = "Untitled Note"
    summary: Optional[str] = None
    action_items: List[str] = Field(default_factory=list)
    calendar_events: List[dict] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    mood: str = "Neutral"
    health_data: Optional[dict] = None
    diarization: List[dict] = Field(default_factory=list)
    intent: str = "note"
    suggested_project: str = "Inbox"
    entities: List[str] = Field(default_factory=list)
    priority: int = 4
    notion_properties: dict = Field(default_factory=list)
    explicit_destination_app: Optional[str] = None
    explicit_folder: Optional[str] = None

class TranscriptionResult(TypedDict):
    text: str

class AIAnalysisPack(TypedDict):
    intent: str
    suggested_project: str
    entities: List[str]
    priority: int
    notion_properties: dict
    explicit_destination_app: Optional[str]
    explicit_folder: Optional[str]
