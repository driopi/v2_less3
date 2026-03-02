from __future__ import annotations

import math
import re
from collections import Counter
from typing import List

from app.models.portrait import PortraitCard, PortraitSignal
from app.models.session import Answer

_WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ]+")

HEDGE_MARKERS = (
    "вроде",
    "наверное",
    "может",
    "может быть",
    "кажется",
    "не уверен",
    "не знаю",
    "возможно",
)

CONFIDENCE_MARKERS = (
    "точно",
    "абсолютно",
    "однозначно",
    "100%",
    "уверен",
    "гарантированно",
)

STRESS_MARKERS = (
    "проблем",
    "риск",
    "стресс",
    "срочно",
    "давление",
    "сложно",
    "конфликт",
    "пережив",
    "трев",
    "напряж",
)

POSITIVE_MARKERS = (
    "хорош",
    "отлич",
    "успех",
    "рост",
    "спокой",
    "уверен",
    "рад",
    "получит",
)

NEGATIVE_MARKERS = (
    "плох",
    "ошиб",
    "провал",
    "потер",
    "бою",
    "трудн",
    "непол",
    "дорог",
)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _count_markers(text: str, markers: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(lowered.count(marker) for marker in markers)


class PortraitService:
    def _signal_for_answer(self, answer: Answer, index: int) -> tuple[PortraitSignal, list[str]]:
        text = answer.audio_transcript or ""
        tokens = _WORD_RE.findall(text.lower())
        token_count = max(1, len(tokens))

        hedge_count = _count_markers(text, HEDGE_MARKERS)
        confidence_count = _count_markers(text, CONFIDENCE_MARKERS)
        stress_count = _count_markers(text, STRESS_MARKERS)
        positive_count = _count_markers(text, POSITIVE_MARKERS)
        negative_count = _count_markers(text, NEGATIVE_MARKERS)

        valence = _clamp((positive_count - negative_count) / max(1, positive_count + negative_count), -1.0, 1.0)
        uncertainty = _clamp((hedge_count - 0.5 * confidence_count) / (token_count / 12 + 1), 0.0, 1.0)
        tension = _clamp((stress_count + negative_count + 0.7 * hedge_count) / (token_count / 8 + 1), 0.0, 1.0)

        emotions: list[str] = []
        if tension >= 0.62:
            emotions.append("напряжение")
        if uncertainty >= 0.56:
            emotions.append("осторожность")
        if valence >= 0.2:
            emotions.append("оптимизм")
        elif valence <= -0.2:
            emotions.append("фрустрация")
        if not emotions:
            emotions.append("спокойствие")

        return (
            PortraitSignal(
                question_number=index + 1,
                tension=round(tension, 3),
                uncertainty=round(uncertainty, 3),
                valence=round(valence, 3),
            ),
            emotions,
        )

    def analyze(self, answers: List[Answer]) -> PortraitCard:
        if not answers:
            return PortraitCard(
                emotional_stability=7,
                hidden_tension=4,
                confidence_proxy=6,
                dominant_emotions=["спокойствие"],
                trigger_questions=[],
                recommendation="Недостаточно данных для точного портрета. Нужны ответы на все вопросы.",
                signals=[],
            )

        signals: list[PortraitSignal] = []
        emotion_counter: Counter[str] = Counter()
        tensions: list[float] = []
        uncertainties: list[float] = []

        for idx, answer in enumerate(answers):
            signal, emotions = self._signal_for_answer(answer, idx)
            signals.append(signal)
            tensions.append(signal.tension)
            uncertainties.append(signal.uncertainty)
            emotion_counter.update(emotions)

        mean_tension = sum(tensions) / len(tensions)
        mean_uncertainty = sum(uncertainties) / len(uncertainties)

        avg_jump = 0.0
        if len(tensions) > 1:
            avg_jump = sum(abs(tensions[i] - tensions[i - 1]) for i in range(1, len(tensions))) / (len(tensions) - 1)
        variance = sum((value - mean_tension) ** 2 for value in tensions) / len(tensions)
        stdev = math.sqrt(variance)

        emotional_stability = round(_clamp(10 - (stdev * 14 + avg_jump * 10), 1, 10))
        hidden_tension = round(_clamp(mean_tension * 10 + max(0.0, stdev - 0.12) * 10, 1, 10))
        confidence_proxy = round(_clamp((1 - mean_uncertainty) * 10, 1, 10))

        top_tension = sorted(signals, key=lambda item: item.tension, reverse=True)
        trigger_questions = [item.question_number for item in top_tension if item.tension >= 0.35][:2]
        if len(trigger_questions) < 2:
            for item in top_tension:
                if item.question_number not in trigger_questions:
                    trigger_questions.append(item.question_number)
                if len(trigger_questions) == 2:
                    break

        if hidden_tension >= 7:
            recommendation = "Говорить медленнее в стресс-темах: там растут маркеры напряжения и неопределенности."
        elif confidence_proxy <= 4:
            recommendation = "Уточнять формулировки короче и конкретнее: сейчас много осторожных оговорок."
        else:
            recommendation = "Сохранять текущий темп и добавить больше конкретных цифр в ключевых ответах."

        dominant_emotions = [label for label, _ in emotion_counter.most_common(3)]

        return PortraitCard(
            emotional_stability=emotional_stability,
            hidden_tension=hidden_tension,
            confidence_proxy=confidence_proxy,
            dominant_emotions=dominant_emotions,
            trigger_questions=trigger_questions,
            recommendation=recommendation,
            signals=signals,
        )
