from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.models.question import Question

JobStatus = Literal["queued", "running", "completed", "failed"]
StepStatus = Literal["pending", "running", "completed", "failed"]


class JobStep(BaseModel):
    key: str
    label: str
    status: StepStatus = "pending"
    eta_seconds: int = 0


class JobResult(BaseModel):
    round: int
    questions: List[Question] = Field(default_factory=list)
    round_summary: str
    is_complete: bool
    checklist_preview: Optional[str] = None


class SessionSubmitAcceptedResponse(BaseModel):
    job_id: str
    status: JobStatus
    current_step: Optional[str] = None
    eta_seconds_left: int
    progress_pct: int


class JobStatusResponse(BaseModel):
    job_id: str
    session_id: str
    status: JobStatus
    current_step: Optional[str] = None
    steps: List[JobStep] = Field(default_factory=list)
    eta_seconds_left: int
    progress_pct: int
    error: Optional[str] = None
    result: Optional[JobResult] = None
