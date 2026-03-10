from __future__ import annotations

import json
import logging
import re
from typing import Any, List, Optional

import httpx

from app.config import Settings
from app.models.checklist import ChecklistItem
from app.models.session import Answer
from app.models.tooling import ToolInsight
from app.services.insight_tools import InsightToolsService
from app.services.mcp import MCPToolProvider

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, settings: Settings, mcp_provider: Optional[MCPToolProvider] = None) -> None:
        self.settings = settings
        self._mcp_provider = mcp_provider
        self._insight_tools = InsightToolsService(mcp_provider=mcp_provider)
        self._provider = settings.llm_provider.lower().strip()
        self._model = None

        if self._provider == "anthropic" and settings.anthropic_api_key:
            from langchain_anthropic import ChatAnthropic

            self._model = ChatAnthropic(
                model=settings.llm_model,
                anthropic_api_key=settings.anthropic_api_key,
                temperature=0.2,
            )

    async def _invoke_text(self, prompt: str, timeout_seconds: float = 45.0) -> Optional[str]:
        if self._provider == "anthropic" and self._model is not None:
            response = await self._model.ainvoke(prompt)
            return str(response.content).strip()

        if self._provider == "gemini" and self.settings.gemini_api_key:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.settings.llm_model}:generateContent"
            )
            params = {"key": self.settings.gemini_api_key}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2},
            }
            try:
                async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                    resp = await client.post(url, params=params, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
                )
                if not text:
                    logger.warning("Gemini returned empty response for model '%s'.", self.settings.llm_model)
                return text
            except Exception:
                logger.exception("Gemini request failed for model '%s'.", self.settings.llm_model)
                return None

        return None

    def plan_tools_for_round(
        self,
        *,
        round_number: int,
        topic: str,
        all_answers: List[Answer],
        latest_round_answers: List[Answer],
        target: str,
    ) -> List[str]:
        return self._insight_tools.plan_tools(
            round_number=round_number,
            topic=topic,
            all_answers=all_answers,
            latest_round_answers=latest_round_answers,
            target=target,
        )

    async def run_tools_for_round(
        self,
        *,
        planned_tools: List[str],
        topic: str,
        all_answers: List[Answer],
    ) -> List[ToolInsight]:
        return await self._insight_tools.run_tools(
            planned_tools=planned_tools,
            topic=topic,
            all_answers=all_answers,
        )

    @staticmethod
    def render_tool_context(insights: List[ToolInsight]) -> str:
        return InsightToolsService.render_context(insights)

    async def generate_initial_questions(self, goal: str, topic: str) -> list[str]:
        prompt = (
            "Сгенерируй ровно 3 вопроса для интервью по теме. "
            "Верни JSON-массив строк без пояснений. "
            f"Цель: {goal}. Тема: {topic}."
        )
        response_text = await self._invoke_text(prompt)
        if not response_text:
            return [
                f"Какую главную цель вы хотите достичь в теме '{topic}'?",
                "Какие ограничения по срокам и ресурсам у проекта?",
                "Какие риски вы уже видите на старте?",
            ]

        return self._parse_questions(response_text)

    async def generate_next_questions(
        self,
        goal: str,
        topic: str,
        all_answers: List[Answer],
        round_summaries: List[str],
        next_round: int,
        tool_context: str = "",
    ) -> list[str]:
        previous_questions = [a.question_text for a in all_answers]
        answer_dump = "\n".join(
            [f"- {a.question_text}: {a.audio_transcript}" for a in all_answers]
        )
        summary_dump = "\n".join(round_summaries)
        prompt = (
            "На основе ответов и summary создай ровно 3 уточняющих вопроса. "
            "Новые вопросы не должны дублировать старые. "
            "Верни JSON-массив строк без пояснений.\n"
            f"Цель: {goal}\n"
            f"Тема: {topic}\n"
            f"Раунд: {next_round}\n"
            f"Summary: {summary_dump}\n"
            f"Ответы: {answer_dump}\n"
            f"{tool_context}\n"
        )
        response_text = await self._invoke_text(prompt)
        if response_text:
            parsed = self._parse_questions(response_text)
            unique = self._ensure_distinct_questions(parsed, previous_questions)
            if len(unique) >= 3:
                return unique[:3]

        return self._fallback_next_questions(
            topic=topic,
            next_round=next_round,
            previous_questions=previous_questions,
        )

    async def summarize_round(self, round_number: int, answers: List[Answer]) -> str:
        joined = "\n".join([f"- {a.question_text}: {a.audio_transcript}" for a in answers])
        prompt = (
            "Сделай краткий summary раунда интервью (2-4 предложения).\n"
            f"Раунд: {round_number}\n"
            f"Ответы:\n{joined}"
        )
        response_text = await self._invoke_text(prompt)
        if not response_text:
            return self._fallback_round_summary(round_number, answers)

        return response_text

    async def generate_mock_answers(
        self,
        *,
        goal: str,
        topic: str,
        round_number: int,
        questions: List[str],
    ) -> tuple[list[str], str]:
        question_dump = "\n".join([f"{idx + 1}. {q}" for idx, q in enumerate(questions)])
        prompt = (
            "Ты играешь роль респондента интервью. "
            "Сгенерируй реалистичные короткие ответы на каждый вопрос (1-3 предложения). "
            "Верни строго JSON-массив строк той же длины, что и список вопросов, без комментариев.\n"
            f"Цель интервью: {goal}\n"
            f"Тема: {topic}\n"
            f"Раунд: {round_number}\n"
            f"Вопросы:\n{question_dump}\n"
        )
        # Mock mode should stay fast; do not block user for long.
        response_text = await self._invoke_text(prompt, timeout_seconds=12.0)
        if response_text:
            parsed = self._parse_questions(response_text)
            if len(parsed) >= len(questions):
                return parsed[: len(questions)], "llm"

        fallback = []
        for idx, question in enumerate(questions, start=1):
            fallback.append(
                self._mock_fallback_answer_for_question(
                    topic=topic,
                    question=question,
                    round_number=round_number,
                    question_index=idx,
                )
            )
        return fallback[: len(questions)], "fallback"

    def _mock_fallback_answer_for_question(
        self,
        *,
        topic: str,
        question: str,
        round_number: int,
        question_index: int,
    ) -> str:
        q = question.lower()
        is_tennis = "теннис" in topic.lower()

        if "цель" in q or "итог" in q:
            if is_tennis:
                return (
                    "Главная цель турнира: провести событие без срывов и получить минимум 180 участников, "
                    "из них не менее 40 корпоративных гостей. Финальный KPI: NPS участников выше 8/10."
                )
            return (
                "Главная цель: запустить пилот и за 4 недели получить измеримый эффект по скорости процесса не менее 20%."
            )

        if "срок" in q or "бюджет" in q or "ресурс" in q:
            if is_tennis:
                return (
                    "Срок подготовки 6 недель, общий бюджет 1.2 млн рублей. Команда: 1 продюсер, 2 координатора, "
                    "8 волонтеров в день мероприятия."
                )
            return (
                "Ограничения: дедлайн 5 недель, бюджет ограничен и без расширения штата; критично уложиться в текущую команду."
            )

        if "риск" in q:
            if is_tennis:
                return (
                    "Ключевые риски: погода, накладки расписания кортов, задержки подрядчиков. Снижение: резервный слот, "
                    "дублирующий подрядчик, ежедневный контрольный чек-лист."
                )
            return (
                "Риски: задержка согласований и низкая полнота данных. План: weekly review, владелец решения, контрольные точки."
            )

        if "данн" in q:
            return (
                "Сейчас есть базовые данные за прошлые периоды, но не хватает структуры по сегментам и качеству. "
                "Нужно добавить единый словарь полей и валидацию."
            )

        if "процесс" in q and ("потерь" in q or "потер" in q):
            if is_tennis:
                return (
                    "Сейчас процесс такой: регистрация участников в таблице, ручная сверка оплат, затем ручная сетка матчей. "
                    "Самая дорогая точка потерь — ручное перепланирование расписания кортов в день турнира."
                )
            return (
                "Текущий процесс в основном ручной: данные собираются в таблицах, согласования идут в чатах. "
                "Самая дорогая потеря — задержка на ручной консолидации и повторных правках."
            )

        if "решение" in q and ("после" in q or "сразу" in q):
            if is_tennis:
                return (
                    "После интервью нужно утвердить формат турнира и лимит бюджета, назначить владельца проекта и "
                    "зафиксировать календарный план подготовки на 6 недель с контрольными точками."
                )
            return (
                "После интервью нужно утвердить go/no-go пилота, назначить владельца результата и подтвердить план внедрения по этапам."
            )

        if "метрик" in q or "kpi" in q or "критер" in q:
            return (
                "Фиксируем 3 KPI: срок цикла, конверсия ключевого этапа и доля ручных операций. "
                "Порог успеха пилота: улучшение минимум на 15%."
            )

        if "кто" in q or "рол" in q or "владел" in q:
            return (
                "Владелец результата — руководитель проекта. Нужны роли: аналитик, техлид, ответственный за операционный процесс."
            )

        # Generic but non-identical fallback.
        return (
            f"Раунд {round_number}, вопрос {question_index}: по теме '{topic}' фиксируем конкретный следующий шаг, "
            "ответственного и измеримый критерий результата, чтобы решение можно было принять сразу после интервью."
        )

    def ensure_distinct_round_summary(
        self,
        round_number: int,
        answers: List[Answer],
        previous_summaries: List[str],
        candidate: str,
    ) -> str:
        normalized_candidate = self._normalize_summary(candidate)
        if not normalized_candidate:
            return self._fallback_round_summary(round_number, answers)

        normalized_previous = {self._normalize_summary(item) for item in previous_summaries}
        if normalized_candidate in normalized_previous:
            return self._fallback_round_summary(round_number, answers)

        return candidate.strip()

    async def build_final_checklist(
        self,
        goal: str,
        topic: str,
        answers: List[Answer],
        round_summaries: List[str],
        tool_context: str = "",
    ) -> list[ChecklistItem]:
        answers_dump = "\n".join([f"- {a.question_text}: {a.audio_transcript}" for a in answers])
        summary_dump = "\n".join(round_summaries)

        prompt = (
            "Построй итоговый checklist в JSON. Формат: "
            "[{\"category\": str, \"item\": str, \"status\": "
            "\"confirmed\"|\"needs_clarification\"|\"not_discussed\", \"notes\": str|null}]\n"
            f"Цель: {goal}\nТема: {topic}\n"
            f"Summary: {summary_dump}\n"
            f"Ответы:\n{answers_dump}\n"
            f"{tool_context}\n"
            "Верни только JSON-массив."
        )

        response_text = await self._invoke_text(prompt)
        if not response_text:
            return [
                ChecklistItem(
                    category="📋 Общая информация",
                    item="Сформулирована цель проекта",
                    status="confirmed",
                    notes="Подтверждено в интервью",
                ),
                ChecklistItem(
                    category="⏰ Сроки и бюджет",
                    item="Уточнить бюджет",
                    status="needs_clarification",
                    notes="Не прозвучали точные числа",
                ),
                ChecklistItem(
                    category="🔧 Технические требования",
                    item="Определить интеграции",
                    status="confirmed",
                    notes="Упомянуты в ответах",
                ),
            ]

        content = response_text
        try:
            data = json.loads(content)
            return [ChecklistItem.model_validate(item) for item in data]
        except Exception:
            return [
                ChecklistItem(
                    category="📋 Итог",
                    item="Требуется ручная валидация сгенерированного чеклиста",
                    status="needs_clarification",
                    notes=content[:240],
                )
            ]

    def _parse_questions(self, content: Any) -> list[str]:
        if isinstance(content, list):
            items = [str(x).strip() for x in content if str(x).strip()]
            return items[:3]

        raw = str(content).strip()

        # Handle markdown code fences like ```json ... ```
        raw_no_fence = raw.replace("```json", "").replace("```", "").strip()

        # Try to extract a JSON array from mixed text.
        array_match = re.search(r"\[[\s\S]*\]", raw_no_fence)
        if array_match:
            try:
                parsed = json.loads(array_match.group(0))
                if isinstance(parsed, list):
                    out = [str(x).strip().strip('"') for x in parsed if str(x).strip()]
                    if len(out) >= 3:
                        return out[:3]
            except Exception:
                pass

        try:
            parsed = json.loads(raw_no_fence)
            if isinstance(parsed, list):
                out = [str(x).strip() for x in parsed if str(x).strip()]
                if len(out) >= 3:
                    return out[:3]
            if isinstance(parsed, dict):
                maybe = parsed.get("questions")
                if isinstance(maybe, list):
                    out = [str(x).strip() for x in maybe if str(x).strip()]
                    if len(out) >= 3:
                        return out[:3]
        except Exception:
            pass

        lines = []
        for line in raw_no_fence.splitlines():
            cleaned = line.strip().strip('"')
            cleaned = re.sub(r"^\d+[\).\s-]+", "", cleaned)  # 1. / 1) / 1-
            cleaned = cleaned.strip("-• \n\t")
            if not cleaned:
                continue
            if cleaned in {"[", "]", "{", "}", ","}:
                continue
            if cleaned.lower() == "json":
                continue
            lines.append(cleaned)

        if len(lines) >= 3:
            return lines[:3]

        return [
            "Расскажите подробнее о текущей ситуации клиента.",
            "Какой результат вы считаете успешным?",
            "Что обязательно учесть при запуске?",
        ]

    @staticmethod
    def _normalize_question(text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip().lower()
        return cleaned.rstrip("?.!,:;")

    def _ensure_distinct_questions(self, questions: list[str], previous_questions: list[str]) -> list[str]:
        used = {self._normalize_question(q) for q in previous_questions}
        out: list[str] = []
        for q in questions:
            candidate = q.strip()
            if not candidate:
                continue
            norm = self._normalize_question(candidate)
            if norm in used:
                continue
            used.add(norm)
            out.append(candidate)
            if len(out) == 3:
                break
        return out

    def _fallback_next_questions(self, topic: str, next_round: int, previous_questions: list[str]) -> list[str]:
        if next_round <= 2:
            pool = [
                f"Какие данные по теме '{topic}' у вас уже есть и чего не хватает для старта?",
                "Как сейчас выглядит целевой процесс без ИИ и где самая дорогая точка потерь?",
                "Какие ограничения по людям, бюджету и срокам нужно учесть до пилота?",
                "Как вы измерите эффект пилота через 2-4 недели?",
                "Какие интеграции с текущими системами обязательны в первой версии?",
            ]
        else:
            pool = [
                f"Какое решение по теме '{topic}' должно быть принято сразу после этого интервью?",
                "Какие риски с высокой вероятностью сорвут запуск и как вы их будете снижать?",
                "Кто владелец результата и какие роли нужны на этапе внедрения?",
                "Какой план запуска по этапам: пилот, масштабирование, контроль качества?",
                "Какие критерии стопа/продолжения проекта вы зафиксируете для руководства?",
            ]

        unique = self._ensure_distinct_questions(pool, previous_questions)
        while len(unique) < 3:
            unique.append(f"Уточните ключевой приоритет этапа {next_round}, который еще не обсуждали.")
        return unique[:3]

    @staticmethod
    def _shorten(text: str, limit: int = 120) -> str:
        single_line = re.sub(r"\s+", " ", text).strip()
        if len(single_line) <= limit:
            return single_line
        return single_line[: limit - 1].rstrip() + "…"

    @staticmethod
    def _normalize_summary(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().lower().strip(".,!?;:")

    def _fallback_round_summary(self, round_number: int, answers: List[Answer]) -> str:
        if not answers:
            return f"Раунд {round_number}: зафиксированы вводные, нужны дополнительные детали."

        parts = []
        for ans in answers[:3]:
            transcript = self._shorten(ans.audio_transcript, limit=90)
            if not transcript:
                transcript = "нет явного ответа"
            parts.append(f"{self._shorten(ans.question_text, limit=55)} — {transcript}")

        return f"Раунд {round_number}: " + " | ".join(parts)
