from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache
from typing import Any, List

from app.config import Settings
from app.models.portrait import PortraitCard, PortraitSignal, PortraitTrigger
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

TENSION_LABELS = ("anger", "annoyance", "fear", "nervousness", "sadness", "disappointment", "grief", "remorse")
NEGATIVE_LABELS = ("anger", "annoyance", "fear", "sadness", "disappointment", "grief", "remorse")
POSITIVE_LABELS = ("joy", "optimism", "gratitude", "love", "approval", "relief", "pride", "admiration")
UNCERTAINTY_LABELS = ("nervousness", "fear", "confusion", "realization")


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _count_markers(text: str, markers: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(lowered.count(marker) for marker in markers)


def _label_sum(scores: dict[str, float], labels: tuple[str, ...]) -> float:
    total = 0.0
    for label, score in scores.items():
        if any(token in label for token in labels):
            total += score
    return _clamp(total, 0.0, 1.0)


def _friendly_label(label: str) -> str:
    mapping = {
        "joy": "радость",
        "optimism": "оптимизм",
        "gratitude": "благодарность",
        "approval": "уверенность",
        "nervousness": "волнение",
        "fear": "тревога",
        "sadness": "грусть",
        "anger": "раздражение",
        "annoyance": "раздражение",
        "confusion": "сомнение",
        "neutral": "спокойствие",
    }
    return mapping.get(label, label)


class PortraitService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.mode = settings.emotion_mode.lower().strip()

    @staticmethod
    @lru_cache(maxsize=1)
    def _get_classifier(model_name: str):
        from transformers import pipeline

        return pipeline("text-classification", model=model_name, device="cpu")

    def _model_scores(self, text: str) -> dict[str, float]:
        if self.mode != "local":
            return {}
        if not text.strip():
            return {}

        try:
            classifier = self._get_classifier(self.settings.emotion_model)
            raw: Any = classifier(text[:1200], top_k=None, truncation=True, max_length=512)
        except Exception:
            return {}

        rows: list[dict[str, Any]] = []
        if isinstance(raw, list) and raw:
            if isinstance(raw[0], dict):
                rows = [item for item in raw if isinstance(item, dict)]
            elif isinstance(raw[0], list):
                nested = raw[0]
                rows = [item for item in nested if isinstance(item, dict)]

        parsed: dict[str, float] = {}
        for row in rows:
            label = str(row.get("label", "")).strip().lower()
            if not label or label.startswith("label_"):
                continue
            score = float(row.get("score", 0.0))
            if score <= 0:
                continue
            parsed[label] = max(parsed.get(label, 0.0), score)
        return parsed

    def _signal_for_answer(self, answer: Answer, index: int) -> tuple[PortraitSignal, list[str]]:
        text = answer.audio_transcript or ""
        tokens = _WORD_RE.findall(text.lower())
        token_count = max(1, len(tokens))

        hedge_count = _count_markers(text, HEDGE_MARKERS)
        confidence_count = _count_markers(text, CONFIDENCE_MARKERS)
        stress_count = _count_markers(text, STRESS_MARKERS)
        positive_count = _count_markers(text, POSITIVE_MARKERS)
        negative_count = _count_markers(text, NEGATIVE_MARKERS)

        heuristic_valence = _clamp(
            (positive_count - negative_count) / max(1, positive_count + negative_count),
            -1.0,
            1.0,
        )
        heuristic_uncertainty = _clamp((hedge_count - 0.5 * confidence_count) / (token_count / 12 + 1), 0.0, 1.0)
        heuristic_tension = _clamp((stress_count + negative_count + 0.7 * hedge_count) / (token_count / 8 + 1), 0.0, 1.0)

        scores = self._model_scores(text)
        has_model_scores = bool(scores)

        if has_model_scores:
            model_tension = _label_sum(scores, TENSION_LABELS)
            model_uncertainty = _label_sum(scores, UNCERTAINTY_LABELS)
            model_positive = _label_sum(scores, POSITIVE_LABELS)
            model_negative = _label_sum(scores, NEGATIVE_LABELS)
            model_valence = _clamp(model_positive - model_negative, -1.0, 1.0)
            tension = _clamp(0.55 * model_tension + 0.45 * heuristic_tension, 0.0, 1.0)
            uncertainty = _clamp(0.55 * model_uncertainty + 0.45 * heuristic_uncertainty, 0.0, 1.0)
            valence = _clamp(0.55 * model_valence + 0.45 * heuristic_valence, -1.0, 1.0)
            top_labels = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:3]
            emotions = [_friendly_label(label) for label, score in top_labels if score >= 0.14]
        else:
            tension = heuristic_tension
            uncertainty = heuristic_uncertainty
            valence = heuristic_valence
            emotions: list[str] = []
            if tension >= 0.5:
                emotions.append("напряжение")
            if uncertainty >= 0.5:
                emotions.append("осторожность")
            if valence >= 0.2:
                emotions.append("оптимизм")
            elif valence <= -0.2:
                emotions.append("фрустрация")

        if not emotions:
            emotions = ["спокойствие"]

        return (
            PortraitSignal(
                question_number=index + 1,
                round_number=answer.round_number,
                question_in_round=((index % 3) + 1),
                question_text=answer.question_text,
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
                triggers=[],
                recommendation="Недостаточно данных для точного портрета. Нужны ответы на все вопросы.",
                signals=[],
            )

        signals: list[PortraitSignal] = []
        emotion_counter: Counter[str] = Counter()
        tensions: list[float] = []
        uncertainties: list[float] = []

        token_counts = [len(_WORD_RE.findall((answer.audio_transcript or "").lower())) for answer in answers]
        avg_token_count = sum(token_counts) / len(token_counts)

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

        stability_raw = _clamp(1 - (stdev * 1.7 + avg_jump * 1.15), 0.0, 1.0)
        tension_raw = _clamp(mean_tension * 0.9 + max(0.0, stdev - 0.11) * 1.05, 0.0, 1.0)
        short_answer_penalty = 0.22 if avg_token_count < 5 else 0.0
        confidence_raw = _clamp((1 - mean_uncertainty) - short_answer_penalty, 0.0, 1.0)

        emotional_stability = round(_clamp(2.5 + stability_raw * 6.0, 1, 10))
        hidden_tension = round(_clamp(2.0 + tension_raw * 6.0, 1, 10))
        confidence_proxy = round(_clamp(2.0 + confidence_raw * 6.0, 1, 10))

        peak_tension = max(tensions) if tensions else 0.0
        peak_uncertainty = max(uncertainties) if uncertainties else 0.0
        triggers: list[PortraitTrigger] = []

        if peak_tension >= 0.3 or peak_uncertainty >= 0.34:
            top_signals = sorted(signals, key=lambda item: max(item.tension, item.uncertainty), reverse=True)
            trigger_threshold = max(0.32, mean_tension + 0.08)
            for signal in top_signals:
                peak_score = max(signal.tension, signal.uncertainty)
                if peak_score < trigger_threshold:
                    continue
                reason = "рост напряжения" if signal.tension >= signal.uncertainty else "рост неопределенности"
                triggers.append(
                    PortraitTrigger(
                        question_number=signal.question_number,
                        round_number=signal.round_number,
                        question_in_round=signal.question_in_round,
                        question_text=signal.question_text,
                        reason=reason,
                        score=round(peak_score, 3),
                    )
                )
                if len(triggers) == 2:
                    break

        trigger_questions = [item.question_number for item in triggers]

        if hidden_tension >= 7:
            recommendation = "Говорить медленнее в стресс-темах: там растут маркеры напряжения и неопределенности."
        elif confidence_proxy <= 4:
            recommendation = "Уточнять формулировки короче и конкретнее: сейчас много осторожных оговорок."
        elif not triggers:
            recommendation = "Сохранять текущий темп: резких эмоциональных триггеров по ответам не выявлено."
        else:
            recommendation = "Добавить больше конкретики в триггерных вопросах и фиксировать метрики сразу в ответе."

        dominant_emotions = [label for label, _ in emotion_counter.most_common(3)]

        return PortraitCard(
            emotional_stability=emotional_stability,
            hidden_tension=hidden_tension,
            confidence_proxy=confidence_proxy,
            dominant_emotions=dominant_emotions,
            trigger_questions=trigger_questions,
            triggers=triggers,
            recommendation=recommendation,
            signals=signals,
        )
