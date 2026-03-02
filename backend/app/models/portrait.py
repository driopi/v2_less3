from typing import List

from pydantic import BaseModel, Field


class PortraitSignal(BaseModel):
    question_number: int
    round_number: int
    question_in_round: int
    question_text: str
    tension: float
    uncertainty: float
    valence: float


class PortraitTrigger(BaseModel):
    question_number: int
    round_number: int
    question_in_round: int
    question_text: str
    reason: str
    score: float


class PortraitCard(BaseModel):
    emotional_stability: int = Field(ge=1, le=10)
    hidden_tension: int = Field(ge=1, le=10)
    confidence_proxy: int = Field(ge=1, le=10)
    dominant_emotions: List[str] = Field(default_factory=list)
    trigger_questions: List[int] = Field(default_factory=list)
    triggers: List[PortraitTrigger] = Field(default_factory=list)
    recommendation: str
    signals: List[PortraitSignal] = Field(default_factory=list)
