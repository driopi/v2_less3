from __future__ import annotations

import asyncio
import base64
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response

from app.agent.state import AgentState
from app.models.session import (
    Answer,
    SessionData,
    SessionResultsResponse,
    SessionStartResponse,
    SessionSubmitResponse,
    StartSessionRequest,
)

router = APIRouter(prefix="/api/session", tags=["session"])


def _decode_base64_audio(encoded: str) -> bytes:
    try:
        return base64.b64decode(encoded.encode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid audio_base64 payload") from exc


@router.post("/start", response_model=SessionStartResponse)
async def start_session(payload: StartSessionRequest, request: Request):
    session_id = str(uuid4())
    graph_service = request.app.state.graph_service
    session_store = request.app.state.session_store

    initial_state: AgentState = {
        "session_id": session_id,
        "goal": payload.goal,
        "topic": payload.topic,
        "current_round": 1,
        "max_rounds": 3,
        "current_questions": [],
        "all_answers": [],
        "latest_round_answers": [],
        "round_summaries": [],
        "round_summary": "",
        "checklist_items": [],
        "markdown_content": "",
        "is_complete": False,
    }

    output = await graph_service.start(initial_state)
    session = SessionData(
        session_id=session_id,
        goal=payload.goal,
        topic=payload.topic,
        current_round=output["current_round"],
        max_rounds=3,
        current_questions=output["current_questions"],
    )
    session_store.create(session)

    return SessionStartResponse(
        session_id=session_id,
        round=session.current_round,
        questions=session.current_questions,
    )


@router.get("/{session_id}", response_model=SessionStartResponse)
async def get_session(session_id: str, request: Request):
    store = request.app.state.session_store
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionStartResponse(
        session_id=session.session_id,
        round=session.current_round,
        questions=session.current_questions,
    )


@router.post("/transcribe")
async def transcribe_audio(request: Request):
    transcription_service = request.app.state.transcription_service
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        audio_file = form.get("audio_file")
        if audio_file is None:
            raise HTTPException(status_code=422, detail="audio_file is required")
        audio_bytes = await audio_file.read()
        filename = getattr(audio_file, "filename", "audio.webm") or "audio.webm"
    else:
        payload = await request.json()
        encoded = payload.get("audio_base64")
        if not encoded:
            raise HTTPException(status_code=422, detail="audio_base64 is required for JSON mode")
        audio_bytes = _decode_base64_audio(encoded)
        filename = payload.get("filename", "audio.webm")

    transcript = await transcription_service.transcribe(audio_bytes, filename=filename)
    return {"transcript": transcript}


@router.post("/{session_id}/submit", response_model=SessionSubmitResponse)
async def submit_answers(
    session_id: str,
    request: Request,
):
    store = request.app.state.session_store
    graph_service = request.app.state.graph_service
    transcription_service = request.app.state.transcription_service

    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.is_complete:
        raise HTTPException(status_code=400, detail="Session already completed")

    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        raw_question_ids = str(form.get("question_ids", ""))
        audio_files = form.getlist("audio_files")
        files_payload = []
        for item in audio_files:
            file_bytes = await item.read()
            files_payload.append((file_bytes, getattr(item, "filename", "audio.webm") or "audio.webm"))
    else:
        payload = await request.json()
        raw_question_ids = str(payload.get("question_ids", ""))
        encoded_files = payload.get("audio_base64_files", [])
        files_payload = [(_decode_base64_audio(encoded), f"answer-{idx + 1}.webm") for idx, encoded in enumerate(encoded_files)]

    question_id_list = [item.strip() for item in raw_question_ids.split(",") if item.strip()]
    if len(files_payload) != 3 or len(question_id_list) != 3:
        raise HTTPException(status_code=422, detail="Expected 3 audio files and 3 question IDs")

    current_question_map = {q.id: q.text for q in session.current_questions}

    round_answers: list[Answer] = []
    for idx, (audio_bytes, filename) in enumerate(files_payload):
        transcript = await transcription_service.transcribe(audio_bytes, filename=filename)
        qid = question_id_list[idx]
        round_answers.append(
            Answer(
                question_id=qid,
                question_text=current_question_map.get(qid, f"Question {idx + 1}"),
                audio_transcript=transcript,
                round_number=session.current_round,
            )
        )

    all_answers = [*session.all_answers, *round_answers]

    state: AgentState = {
        "session_id": session.session_id,
        "goal": session.goal,
        "topic": session.topic,
        "current_round": session.current_round,
        "max_rounds": session.max_rounds,
        "current_questions": session.current_questions,
        "all_answers": all_answers,
        "latest_round_answers": round_answers,
        "round_summaries": session.round_summaries,
        "round_summary": "",
        "checklist_items": session.checklist_items,
        "markdown_content": session.markdown_content,
        "is_complete": session.is_complete,
    }

    try:
        # Final round may include slower LLM/MCP calls; guard against infinite waits.
        output = await asyncio.wait_for(graph_service.advance(state), timeout=120.0)
    except asyncio.TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail="Обработка раунда заняла слишком много времени. Повторите отправку.",
        ) from exc

    session.current_round = output["current_round"]
    session.current_questions = output.get("current_questions", [])
    session.all_answers = all_answers
    session.round_summaries = output.get("round_summaries", session.round_summaries)
    session.checklist_items = output.get("checklist_items", session.checklist_items)
    session.markdown_content = output.get("markdown_content", session.markdown_content)
    session.is_complete = output.get("is_complete", False)
    store.update(session)

    return SessionSubmitResponse(
        round=session.current_round,
        questions=session.current_questions,
        round_summary=output.get("round_summary", ""),
        is_complete=session.is_complete,
        checklist_preview=session.markdown_content if session.is_complete else None,
    )


@router.get("/{session_id}/results", response_model=SessionResultsResponse)
async def get_results(session_id: str, request: Request):
    store = request.app.state.session_store
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResultsResponse(
        session_id=session.session_id,
        is_complete=session.is_complete,
        checklist=session.checklist_items,
        markdown=session.markdown_content,
        round_summaries=session.round_summaries,
    )


@router.get("/{session_id}/download")
async def download_markdown(session_id: str, request: Request):
    store = request.app.state.session_store
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.is_complete or not session.markdown_content:
        raise HTTPException(status_code=400, detail="Session is not completed")

    headers = {
        "Content-Disposition": f"attachment; filename=checklist-{session_id}.md",
    }
    return PlainTextResponse(content=session.markdown_content, headers=headers)


@router.get("/{session_id}/summary-audio")
async def get_summary_audio(session_id: str, request: Request):
    store = request.app.state.session_store
    tts_service = request.app.state.tts_service

    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.is_complete:
        raise HTTPException(status_code=400, detail="Session is not completed")

    audio_bytes, content_type, source = await tts_service.synthesize_summary(session)
    return Response(
        content=audio_bytes,
        media_type=content_type,
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f"inline; filename=summary-{session_id}.wav",
            "X-TTS-Source": source,
        },
    )
