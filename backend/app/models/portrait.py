from typing import List

from pydantic import BaseModel, Field


class PortraitSignal(BaseModel):
    question_number: int
    tension: float
    uncertainty: float
    valence: float


class PortraitCard(BaseModel):
    emotional_stability: int = Field(ge=1, le=10)
    hidden_tension: int = Field(ge=1, le=10)
    confidence_proxy: int = Field(ge=1, le=10)
    dominant_emotions: List[str] = Field(default_factory=list)
    trigger_questions: List[int] = Field(default_factory=list)
    recommendation: str
    signals: List[PortraitSignal] = Field(default_factory=list)
