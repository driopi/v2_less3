from __future__ import annotations

import time
from typing import Dict, Optional

from app.models.job import JobResult, JobStatus, JobStatusResponse, JobStep


DEFAULT_STEP_ETAS: dict[str, int] = {
    "transcribe_1": 6,
    "transcribe_2": 6,
    "transcribe_3": 6,
    "analyze_round": 8,
    "tool_planning": 3,
    "tool_execution": 5,
    "generate_next_questions": 6,
    "finalize": 10,
}

STEP_LABELS: dict[str, str] = {
    "transcribe_1": "Транскрибация ответа 1/3",
    "transcribe_2": "Транскрибация ответа 2/3",
    "transcribe_3": "Транскрибация ответа 3/3",
    "analyze_round": "Анализ ответов раунда",
    "tool_planning": "Планирование вызова инструментов",
    "tool_execution": "Выполнение инструментов",
    "generate_next_questions": "Генерация следующих вопросов",
    "finalize": "Генерация финального резюме и чеклиста",
}


class JobRecord:
    def __init__(self, job_id: str, session_id: str, steps: list[JobStep]) -> None:
        self.job_id = job_id
        self.session_id = session_id
        self.status: JobStatus = "queued"
        self.current_step: Optional[str] = None
        self.steps = steps
        self.error: Optional[str] = None
        self.result: Optional[JobResult] = None
        self._started_at = time.monotonic()
        self._step_started_at: Optional[float] = None

    def _eta_left(self) -> int:
        remaining = 0.0
        for step in self.steps:
            if step.status == "completed":
                continue
            if step.status == "running" and self._step_started_at is not None:
                elapsed = max(0.0, time.monotonic() - self._step_started_at)
                remaining += max(0.0, step.eta_seconds - elapsed)
            else:
                remaining += step.eta_seconds
        return int(round(remaining))

    def _progress_pct(self) -> int:
        if not self.steps:
            return 0
        done = sum(1 for step in self.steps if step.status == "completed")
        if self.status == "completed":
            return 100
        return int((done / len(self.steps)) * 100)

    def as_response(self) -> JobStatusResponse:
        return JobStatusResponse(
            job_id=self.job_id,
            session_id=self.session_id,
            status=self.status,
            current_step=self.current_step,
            steps=self.steps,
            eta_seconds_left=self._eta_left(),
            progress_pct=self._progress_pct(),
            error=self.error,
            result=self.result,
        )


class JobStore:
    def __init__(self) -> None:
        self._jobs: Dict[str, JobRecord] = {}
        self._step_etas = dict(DEFAULT_STEP_ETAS)

    def _step_eta(self, key: str) -> int:
        return int(self._step_etas.get(key, 5))

    def create(self, job_id: str, session_id: str, step_keys: list[str]) -> JobRecord:
        steps = [
            JobStep(
                key=step_key,
                label=STEP_LABELS.get(step_key, step_key),
                eta_seconds=self._step_eta(step_key),
            )
            for step_key in step_keys
        ]
        record = JobRecord(job_id=job_id, session_id=session_id, steps=steps)
        self._jobs[job_id] = record
        return record

    def get(self, job_id: str) -> Optional[JobRecord]:
        return self._jobs.get(job_id)

    def mark_running(self, job_id: str) -> None:
        record = self._jobs[job_id]
        record.status = "running"

    def mark_step_running(self, job_id: str, step_key: str) -> None:
        record = self._jobs[job_id]
        record.current_step = step_key
        record._step_started_at = time.monotonic()
        for step in record.steps:
            if step.key == step_key:
                step.status = "running"
                break

    def mark_step_completed(self, job_id: str, step_key: str) -> None:
        record = self._jobs[job_id]
        duration = 0.0
        if record._step_started_at is not None:
            duration = max(0.0, time.monotonic() - record._step_started_at)
        for step in record.steps:
            if step.key == step_key:
                step.status = "completed"
                if duration > 0:
                    prev = float(self._step_etas.get(step.key, step.eta_seconds))
                    self._step_etas[step.key] = max(1, int(round(prev * 0.75 + duration * 0.25)))
                break
        record._step_started_at = None

    def mark_failed(self, job_id: str, error: str) -> None:
        record = self._jobs[job_id]
        record.status = "failed"
        record.error = error
        if record.current_step:
            for step in record.steps:
                if step.key == record.current_step and step.status == "running":
                    step.status = "failed"
                    break

    def mark_completed(self, job_id: str, result: JobResult) -> None:
        record = self._jobs[job_id]
        record.status = "completed"
        record.result = result
        record.current_step = None
        for step in record.steps:
            if step.status == "running":
                step.status = "completed"
