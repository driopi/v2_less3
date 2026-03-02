from typing import List, Optional, TypedDict

from app.models.checklist import ChecklistItem
from app.models.portrait import PortraitCard
from app.models.question import Question
from app.models.session import Answer


class AgentState(TypedDict):
    session_id: str
    goal: str
    topic: str
    current_round: int
    max_rounds: int
    current_questions: List[Question]
    all_answers: List[Answer]
    latest_round_answers: List[Answer]
    round_summaries: List[str]
    round_summary: str
    checklist_items: List[ChecklistItem]
    portrait: Optional[PortraitCard]
    markdown_content: str
    is_complete: bool
