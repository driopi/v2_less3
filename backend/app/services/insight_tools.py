from __future__ import annotations

import asyncio
import re
import sqlite3
from collections import Counter
from typing import Any, Dict, List, Optional

from app.models.session import Answer
from app.models.tooling import ToolInsight
from app.services.mcp import MCPToolProvider

_RU_STOPWORDS = {
    "и",
    "в",
    "во",
    "на",
    "по",
    "с",
    "со",
    "к",
    "у",
    "для",
    "из",
    "а",
    "но",
    "что",
    "как",
    "это",
    "мы",
    "вы",
    "они",
    "он",
    "она",
    "не",
    "да",
    "или",
    "ли",
    "бы",
    "быть",
    "есть",
    "будет",
    "уже",
    "еще",
    "очень",
    "тема",
    "проект",
}

_UNCERTAINTY_MARKERS = (
    "не знаю",
    "наверно",
    "наверное",
    "возможно",
    "может быть",
    "пока не",
    "сложно сказать",
    "уточнить",
    "не уверен",
)

_CALCULATOR_HINTS = (
    "бюджет",
    "срок",
    "дней",
    "недель",
    "месяц",
    "процент",
    "%",
    "стоимость",
    "цена",
    "доход",
    "расход",
)


class InsightToolsService:
    def __init__(self, mcp_provider: Optional[MCPToolProvider] = None) -> None:
        self._mcp_provider = mcp_provider

    def plan_tools(
        self,
        *,
        round_number: int,
        topic: str,
        all_answers: List[Answer],
        latest_round_answers: List[Answer],
        target: str,
    ) -> List[str]:
        planned = ["session_db"]

        transcript_pool = " ".join(a.audio_transcript.lower() for a in latest_round_answers or all_answers)
        has_digits = bool(re.search(r"\d", transcript_pool))
        has_calc_hints = any(hint in transcript_pool for hint in _CALCULATOR_HINTS)

        if target == "next_questions" or round_number <= 2:
            planned.append("research")

        if has_digits or has_calc_hints:
            planned.append("calculator")

        # Keep tool set stable for final round even when numbers are absent.
        if target == "final_checklist" and "calculator" not in planned:
            planned.append("calculator")

        # Preserve order, remove accidental duplicates.
        ordered_unique: list[str] = []
        for item in planned:
            if item not in ordered_unique:
                ordered_unique.append(item)
        return ordered_unique

    async def run_tools(
        self,
        *,
        planned_tools: List[str],
        topic: str,
        all_answers: List[Answer],
    ) -> List[ToolInsight]:
        out: list[ToolInsight] = []
        for tool_name in planned_tools:
            if tool_name == "session_db":
                out.append(self._session_db_tool(all_answers))
            elif tool_name == "calculator":
                out.append(self._calculator_tool(all_answers))
            elif tool_name == "research":
                out.append(await self._research_tool(topic))
        return out

    @staticmethod
    def render_context(insights: List[ToolInsight]) -> str:
        if not insights:
            return ""
        lines = ["Инструментальные наблюдения:"]
        for idx, insight in enumerate(insights, start=1):
            details = "; ".join(f"{k}: {v}" for k, v in insight.details.items() if str(v).strip())
            if details:
                lines.append(f"{idx}. {insight.title}: {insight.summary} ({details})")
            else:
                lines.append(f"{idx}. {insight.title}: {insight.summary}")
        return "\n".join(lines)

    def _session_db_tool(self, answers: List[Answer]) -> ToolInsight:
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute(
                "CREATE TABLE answers (round_number INTEGER, question_text TEXT, transcript TEXT)"
            )
            conn.executemany(
                "INSERT INTO answers(round_number, question_text, transcript) VALUES (?, ?, ?)",
                [(a.round_number, a.question_text, a.audio_transcript) for a in answers],
            )
            row = conn.execute(
                "SELECT COUNT(*), AVG(LENGTH(transcript)), COUNT(DISTINCT round_number) FROM answers"
            ).fetchone()
            total_answers = int(row[0] or 0)
            avg_len = int(round(float(row[1] or 0.0)))
            rounds_covered = int(row[2] or 0)

            joined = " ".join(a.audio_transcript.lower() for a in answers)
            tokens = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]{3,}", joined)
            words = [w for w in tokens if w not in _RU_STOPWORDS and not w.isdigit()]
            top_words = [word for word, _count in Counter(words).most_common(5)]
            uncertainty_hits = sum(1 for marker in _UNCERTAINTY_MARKERS if marker in joined)

            summary = (
                f"В базе {total_answers} ответов по {rounds_covered} раундам; "
                f"средняя длина ответа {avg_len} символов."
            )
            details = {
                "топ-темы": ", ".join(top_words) if top_words else "нет выраженных тем",
                "маркеры_неопределенности": str(uncertainty_hits),
            }
            return ToolInsight(
                tool_name="session_db",
                title="Session DB Lens",
                summary=summary,
                details=details,
            )
        finally:
            conn.close()

    def _calculator_tool(self, answers: List[Answer]) -> ToolInsight:
        text = " ".join(a.audio_transcript for a in answers)
        raw_numbers = re.findall(r"\d+(?:[.,]\d+)?", text)
        values = [float(item.replace(",", ".")) for item in raw_numbers]
        percent_mentions = len(re.findall(r"\d+(?:[.,]\d+)?\s*%", text))

        if not values:
            return ToolInsight(
                tool_name="calculator",
                title="Numeric Estimator",
                summary="Числовые ориентиры не обнаружены; стоит запросить KPI, бюджет и сроки в цифрах.",
                details={"чисел": "0", "проценты": str(percent_mentions)},
            )

        avg_value = sum(values) / len(values)
        summary = (
            f"Найдены числовые ориентиры: {len(values)} значений, "
            f"диапазон {min(values):.0f}-{max(values):.0f}, среднее {avg_value:.1f}."
        )
        return ToolInsight(
            tool_name="calculator",
            title="Numeric Estimator",
            summary=summary,
            details={
                "чисел": str(len(values)),
                "минимум": f"{min(values):.0f}",
                "максимум": f"{max(values):.0f}",
                "проценты": str(percent_mentions),
            },
        )

    async def _research_tool(self, topic: str) -> ToolInsight:
        fallback = self._fallback_research(topic)
        if self._mcp_provider is None:
            return fallback

        try:
            tools = await asyncio.wait_for(self._mcp_provider.get_tools(), timeout=8.0)
        except Exception:
            return fallback

        if not tools:
            return fallback

        for tool in tools[:2]:
            try:
                result = await asyncio.wait_for(tool.ainvoke({"query": topic}), timeout=7.0)
            except Exception:
                try:
                    result = await asyncio.wait_for(tool.ainvoke(topic), timeout=7.0)
                except Exception:
                    continue
            text = re.sub(r"\s+", " ", str(result)).strip()
            if not text:
                continue
            snippet = text[:260]
            return ToolInsight(
                tool_name="research",
                title="Research Probe",
                summary=f"MCP-результат по теме '{topic}': {snippet}",
                details={"источник": "mcp", "длина": str(len(text))},
            )

        return fallback

    @staticmethod
    def _fallback_research(topic: str) -> ToolInsight:
        normalized = topic.lower()
        if "теннис" in normalized:
            summary = (
                "Для турниров критичны логистика кортов, сетка матчей, судейство, "
                "питание и сценарий непогоды."
            )
            notes = "расписание, регламент, риски переноса"
        else:
            summary = (
                "Для discovery-интервью обычно важны KPI, владелец процесса, "
                "ограничения бюджета/сроков и критерии успеха пилота."
            )
            notes = "kpi, роли, дедлайны, критерии stop/go"

        return ToolInsight(
            tool_name="research",
            title="Research Probe",
            summary=summary,
            details={"источник": "fallback", "ключевые_узлы": notes},
        )
