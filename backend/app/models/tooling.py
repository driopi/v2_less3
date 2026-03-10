from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, Field


class ToolInsight(BaseModel):
    tool_name: str
    title: str
    summary: str
    details: Dict[str, str] = Field(default_factory=dict)
