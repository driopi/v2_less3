from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.checklist import ChecklistItem
from app.models.portrait import PortraitCard
from app.models.question import Question
from app.models.tooling import ToolInsight


class StartSessionRequest(BaseModel):
    goal: str = Field(default="Заполнить чеклист созвона с клиентом")
    topic: str = Field(default="Бриф по проекту")


class Answer(BaseModel):
    question_id: str
    question_text: str
    audio_transcript: str
    round_number: int


class SessionData(BaseModel):
    session_id: str
    goal: str
    topic: str
    current_round: int = 1
    max_rounds: int = 3
    current_questions: List[Question] = Field(default_factory=list)
    all_answers: List[Answer] = Field(default_factory=list)
    round_summaries: List[str] = Field(default_factory=list)
    checklist_items: List[ChecklistItem] = Field(default_factory=list)
    tool_insights: List[ToolInsight] = Field(default_factory=list)
    portrait: Optional[PortraitCard] = None
    markdown_content: str = ""
    is_complete: bool = False


class SessionStartResponse(BaseModel):
    session_id: str
    round: int
    questions: List[Question]


class SessionSubmitResponse(BaseModel):
    round: int
    questions: List[Question] = []
    round_summary: str
    is_complete: bool
    checklist_preview: Optional[str] = None


class SessionResultsResponse(BaseModel):
    session_id: str
    is_complete: bool
    checklist: List[ChecklistItem]
    tool_insights: List[ToolInsight]
    markdown: str
    round_summaries: List[str]
    portrait: Optional[PortraitCard] = None
