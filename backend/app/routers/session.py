from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response

from app.agent.state import AgentState
from app.models.job import JobResult, JobStatusResponse, SessionSubmitAcceptedResponse
from app.models.question import Question
from app.models.session import (
    Answer,
    MockAnswerPreview,
    MockAnswersResponse,
    SessionData,
    SessionLogEntry,
    SessionResultsResponse,
    SessionStartResponse,
    StartSessionRequest,
)
from app.services.file_generator import build_markdown

router = APIRouter(prefix="/api/session", tags=["session"])


def _decode_base64_audio(encoded: str) -> bytes:
    try:
        return base64.b64decode(encoded.encode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid audio_base64 payload") from exc


def _job_steps_for_round(current_round: int, max_rounds: int) -> list[str]:
    steps = ["transcribe_1", "transcribe_2", "transcribe_3", "analyze_round", "tool_planning", "tool_execution"]
    if current_round < max_rounds:
        steps.append("generate_next_questions")
    else:
        steps.append("finalize")
    return steps


def _to_questions(texts: list[str]) -> list[Question]:
    return [Question(id=str(uuid4()), text=text) for text in texts[:3]]


def _now_hms_utc() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def _append_session_log(session: SessionData, source: str, message: str) -> None:
    session.logs.append(SessionLogEntry(at=_now_hms_utc(), source=source, message=message))


def _mock_initial_question_texts() -> list[str]:
    return [
        "Какую главную цель вы хотите достичь по итогам интервью?",
        "Какие ограничения по срокам, бюджету и ресурсам критичны на старте?",
        "Какие ключевые риски вы видите сейчас и как планируете их снижать?",
    ]


def _mock_initial_answer_texts(topic: str) -> list[str]:
    if "теннис" in topic.lower():
        return [
            "Цель: провести турнир без срывов, собрать не менее 180 участников и получить NPS выше 8/10.",
            "Ограничения: подготовка 6 недель, бюджет 1.2 млн рублей, команда 1 продюсер + 2 координатора + 8 волонтеров в день события.",
            "Риски: погода, пересечения по кортам и задержки подрядчиков; снижаем резервным планом, буфером времени и ежедневным контрольным листом.",
        ]
    return [
        "Цель: зафиксировать решение по запуску пилота и ожидаемый бизнес-эффект с конкретными KPI.",
        "Ограничения: фиксированный дедлайн, ограниченный бюджет и работа текущей командой без расширения штата.",
        "Риски: неполные данные и задержки согласований; снижаем через владельца решения, weekly review и контрольные точки.",
    ]


async def _process_submit_job(
    *,
    job_id: str,
    session_id: str,
    question_id_list: list[str],
    files_payload: list[tuple[bytes, str]],
    transcripts_payload: list[str] | None,
    app,
) -> None:
    store = app.state.session_store
    transcription_service = app.state.transcription_service
    llm_service = app.state.llm_service
    portrait_service = app.state.portrait_service
    job_store = app.state.job_store

    try:
        job_store.mark_running(job_id)
        session = store.get(session_id)
        if not session:
            raise RuntimeError("Session not found")
        if session.is_complete:
            raise RuntimeError("Session already completed")

        current_question_map = {q.id: q.text for q in session.current_questions}
        round_answers: list[Answer] = []

        for idx, qid in enumerate(question_id_list):
            step_key = f"transcribe_{idx + 1}"
            job_store.mark_step_running(job_id, step_key)
            if transcripts_payload is not None:
                transcript = transcripts_payload[idx].strip()
            else:
                audio_bytes, filename = files_payload[idx]
                transcript = await transcription_service.transcribe(audio_bytes, filename=filename)
            job_store.mark_step_completed(job_id, step_key)
            round_answers.append(
                Answer(
                    question_id=qid,
                    question_text=current_question_map.get(qid, f"Question {idx + 1}"),
                    audio_transcript=transcript,
                    round_number=session.current_round,
                )
            )

        all_answers = [*session.all_answers, *round_answers]
        _append_session_log(session, "transcribe", f"Раунд {session.current_round}: получено 3 ответа")

        job_store.mark_step_running(job_id, "analyze_round")
        summary_candidate = await llm_service.summarize_round(
            round_number=session.current_round,
            answers=round_answers,
        )
        round_summary = llm_service.ensure_distinct_round_summary(
            round_number=session.current_round,
            answers=round_answers,
            previous_summaries=session.round_summaries,
            candidate=summary_candidate,
        )
        round_summaries = [*session.round_summaries, round_summary]
        _append_session_log(session, "llm", f"Раунд {session.current_round}: сформирован summary")
        job_store.mark_step_completed(job_id, "analyze_round")

        target = "next_questions" if session.current_round < session.max_rounds else "final_checklist"

        job_store.mark_step_running(job_id, "tool_planning")
        planned_tools = llm_service.plan_tools_for_round(
            round_number=session.current_round,
            topic=session.topic,
            all_answers=all_answers,
            latest_round_answers=round_answers,
            target=target,
        )
        _append_session_log(session, "tools", f"План инструментов: {', '.join(planned_tools)}")
        job_store.mark_step_completed(job_id, "tool_planning")

        job_store.mark_step_running(job_id, "tool_execution")
        tool_insights = await llm_service.run_tools_for_round(
            planned_tools=planned_tools,
            topic=session.topic,
            all_answers=all_answers,
        )
        tool_context = llm_service.render_tool_context(tool_insights)
        for insight in tool_insights:
            _append_session_log(
                session,
                "tools",
                f"{insight.tool_name}: {insight.summary}",
            )
        job_store.mark_step_completed(job_id, "tool_execution")

        if session.current_round < session.max_rounds:
            job_store.mark_step_running(job_id, "generate_next_questions")
            next_round = session.current_round + 1
            next_questions_text = await llm_service.generate_next_questions(
                goal=session.goal,
                topic=session.topic,
                all_answers=all_answers,
                round_summaries=round_summaries,
                next_round=next_round,
                tool_context=tool_context,
            )
            next_questions = _to_questions(next_questions_text)
            _append_session_log(
                session,
                "llm",
                f"Раунд {session.current_round}: сгенерированы вопросы раунда {next_round}",
            )
            job_store.mark_step_completed(job_id, "generate_next_questions")

            session.current_round = next_round
            session.current_questions = next_questions
            session.all_answers = all_answers
            session.round_summaries = round_summaries
            session.tool_insights = [*session.tool_insights, *tool_insights]
            session.is_complete = False
            store.update(session)

            job_store.mark_completed(
                job_id,
                JobResult(
                    round=session.current_round,
                    questions=next_questions,
                    round_summary=round_summary,
                    is_complete=False,
                    checklist_preview=None,
                ),
            )
            return

        job_store.mark_step_running(job_id, "finalize")
        checklist = await llm_service.build_final_checklist(
            goal=session.goal,
            topic=session.topic,
            answers=all_answers,
            round_summaries=round_summaries,
            tool_context=tool_context,
        )
        portrait = portrait_service.analyze(all_answers)
        _append_session_log(session, "llm", "Сформирован финальный чеклист и карточка портрета")
        all_tool_insights = [*session.tool_insights, *tool_insights]
        markdown = build_markdown(
            session_id=session.session_id,
            topic=session.topic,
            checklist=checklist,
            answers=all_answers,
            tool_insights=all_tool_insights,
        )
        job_store.mark_step_completed(job_id, "finalize")

        session.current_questions = []
        session.all_answers = all_answers
        session.round_summaries = round_summaries
        session.checklist_items = checklist
        session.portrait = portrait
        session.tool_insights = all_tool_insights
        session.markdown_content = markdown
        session.is_complete = True
        store.update(session)

        job_store.mark_completed(
            job_id,
            JobResult(
                round=session.current_round,
                questions=[],
                round_summary=round_summary,
                is_complete=True,
                checklist_preview=markdown,
            ),
        )
    except Exception as exc:
        job_store.mark_failed(job_id, str(exc))


@router.post("/start", response_model=SessionStartResponse)
async def start_session(payload: StartSessionRequest, request: Request):
    session_id = str(uuid4())
    session_store = request.app.state.session_store
    settings = request.app.state.settings

    if payload.mock_mode:
        current_questions = _to_questions(_mock_initial_question_texts())
    else:
        graph_service = request.app.state.graph_service
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
            "tool_insights": [],
            "portrait": None,
            "markdown_content": "",
            "is_complete": False,
        }
        output = await graph_service.start(initial_state)
        current_questions = output["current_questions"]

    session = SessionData(
        session_id=session_id,
        goal=payload.goal,
        topic=payload.topic,
        current_round=1,
        max_rounds=3,
        mock_mode=payload.mock_mode,
        current_questions=current_questions,
    )
    if payload.mock_mode:
        _append_session_log(session, "system", "Сессия запущена в mock_mode=true. Раунд 1 использует фиксированные вопросы.")
    else:
        _append_session_log(
            session,
            "system",
            f"Сессия запущена в обычном режиме. Генерация вопросов: {settings.llm_provider}/{settings.llm_model}",
        )
    session_store.create(session)

    return SessionStartResponse(
        session_id=session_id,
        round=session.current_round,
        mock_mode=session.mock_mode,
        logs=session.logs,
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
        mock_mode=session.mock_mode,
        logs=session.logs,
        questions=session.current_questions,
    )


@router.post("/{session_id}/mock-answers", response_model=MockAnswersResponse)
async def generate_mock_answers(session_id: str, request: Request):
    store = request.app.state.session_store
    llm_service = request.app.state.llm_service

    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.is_complete:
        raise HTTPException(status_code=400, detail="Session already completed")
    if not session.mock_mode:
        raise HTTPException(status_code=400, detail="Session is not in mock mode")

    questions = session.current_questions
    if len(questions) != 3:
        raise HTTPException(status_code=400, detail="Expected exactly 3 active questions")

    question_texts = [q.text for q in questions]
    if session.current_round == 1 and question_texts == _mock_initial_question_texts():
        transcripts = _mock_initial_answer_texts(session.topic)
        source = "preset_round1"
    else:
        transcripts, source = await llm_service.generate_mock_answers(
            goal=session.goal,
            topic=session.topic,
            round_number=session.current_round,
            questions=question_texts,
        )
    if len(transcripts) < 3:
        transcripts = [
            *transcripts,
            *["Нужны дополнительные вводные по этому пункту." for _ in range(3 - len(transcripts))],
        ]

    logs = [
        "mock_mode=true: аудио не требуется, ответы сгенерированы автоматически",
        f"Источник генерации ответов: {source}",
        f"Раунд {session.current_round}: создано {len(transcripts[:3])} транскриптов",
    ]
    _append_session_log(
        session,
        "mock",
        f"Раунд {session.current_round}: сгенерированы 3 mock-ответа (source={source})",
    )
    store.update(session)
    return MockAnswersResponse(
        session_id=session.session_id,
        round=session.current_round,
        answers=[
            MockAnswerPreview(
                question_id=q.id,
                question_text=q.text,
                transcript=transcripts[idx].strip(),
            )
            for idx, q in enumerate(questions[:3])
        ],
        logs=logs,
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


@router.post("/{session_id}/submit", response_model=SessionSubmitAcceptedResponse)
async def submit_answers(
    session_id: str,
    request: Request,
):
    store = request.app.state.session_store
    job_store = request.app.state.job_store

    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.is_complete:
        raise HTTPException(status_code=400, detail="Session already completed")

    content_type = request.headers.get("content-type", "")
    transcripts_payload: list[str] | None = None
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
        transcripts = payload.get("transcripts", [])
        if transcripts:
            if not session.mock_mode:
                raise HTTPException(status_code=400, detail="transcripts mode is allowed only for mock_mode sessions")
            transcripts_payload = [str(item).strip() for item in transcripts]
            files_payload = []
        else:
            files_payload = [(_decode_base64_audio(encoded), f"answer-{idx + 1}.webm") for idx, encoded in enumerate(encoded_files)]

    question_id_list = [item.strip() for item in raw_question_ids.split(",") if item.strip()]
    if len(question_id_list) != 3:
        raise HTTPException(status_code=422, detail="Expected 3 question IDs")
    if transcripts_payload is not None:
        if len(transcripts_payload) != 3:
            raise HTTPException(status_code=422, detail="Expected 3 transcripts in mock mode")
    elif len(files_payload) != 3:
        raise HTTPException(status_code=422, detail="Expected 3 audio files")

    job_id = str(uuid4())
    record = job_store.create(
        job_id=job_id,
        session_id=session_id,
        step_keys=_job_steps_for_round(session.current_round, session.max_rounds),
    )

    asyncio.create_task(
        _process_submit_job(
            job_id=job_id,
            session_id=session_id,
            question_id_list=question_id_list,
            files_payload=files_payload,
            transcripts_payload=transcripts_payload,
            app=request.app,
        )
    )

    snapshot = record.as_response()
    return SessionSubmitAcceptedResponse(
        job_id=snapshot.job_id,
        status=snapshot.status,
        current_step=snapshot.current_step,
        eta_seconds_left=snapshot.eta_seconds_left,
        progress_pct=snapshot.progress_pct,
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_submit_job(job_id: str, request: Request):
    job_store = request.app.state.job_store
    record = job_store.get(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    return record.as_response()


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
        tool_insights=session.tool_insights,
        logs=session.logs,
        markdown=session.markdown_content,
        round_summaries=session.round_summaries,
        portrait=session.portrait,
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
