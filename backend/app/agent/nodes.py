from __future__ import annotations

import uuid
from typing import List

from app.models.question import Question
from app.services.file_generator import build_markdown


def to_questions(texts: List[str]) -> List[Question]:
    return [Question(id=str(uuid.uuid4()), text=t) for t in texts[:3]]


async def generate_initial_questions_node(state, llm_service):
    texts = await llm_service.generate_initial_questions(state["goal"], state["topic"])
    return {
        "current_round": 1,
        "current_questions": to_questions(texts),
        "is_complete": False,
    }


async def analyze_round_node(state, llm_service):
    summary = await llm_service.summarize_round(state["current_round"], state["latest_round_answers"])
    summary = llm_service.ensure_distinct_round_summary(
        round_number=state["current_round"],
        answers=state["latest_round_answers"],
        previous_summaries=state.get("round_summaries", []),
        candidate=summary,
    )
    round_summaries = [*state.get("round_summaries", []), summary]
    return {
        "round_summary": summary,
        "round_summaries": round_summaries,
    }


def route_after_analyze(state):
    if state["current_round"] < state["max_rounds"]:
        return "next_round"
    return "finalize"


async def generate_next_questions_node(state, llm_service):
    next_round = state["current_round"] + 1
    texts = await llm_service.generate_next_questions(
        goal=state["goal"],
        topic=state["topic"],
        all_answers=state["all_answers"],
        round_summaries=state["round_summaries"],
        next_round=next_round,
    )
    return {
        "current_round": next_round,
        "current_questions": to_questions(texts),
        "is_complete": False,
    }


async def finalize_node(state, llm_service):
    checklist = await llm_service.build_final_checklist(
        goal=state["goal"],
        topic=state["topic"],
        answers=state["all_answers"],
        round_summaries=state["round_summaries"],
    )
    markdown = build_markdown(
        session_id=state["session_id"],
        topic=state["topic"],
        checklist=checklist,
        answers=state["all_answers"],
    )
    return {
        "checklist_items": checklist,
        "markdown_content": markdown,
        "is_complete": True,
        "current_questions": [],
    }
