from __future__ import annotations

import io
import json
import math
import wave
from typing import Tuple

import httpx

from app.config import Settings
from app.models.session import SessionData


class TTSService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        provider = settings.tts_provider.lower().strip()
        if provider == "auto":
            provider = "huggingface" if settings.huggingface_api_key else "mock"
        self.provider = provider

    @property
    def is_available(self) -> bool:
        return self.provider in {"huggingface", "mock"}

    def build_summary_text(self, session: SessionData) -> str:
        lines: list[str] = []
        lines.append(f"Интервью по теме {session.topic} завершено.")
        lines.append("Ключевые выводы:")

        if session.round_summaries:
            for idx, summary in enumerate(session.round_summaries[:3], start=1):
                clean = " ".join(summary.split())
                lines.append(f"Раунд {idx}: {clean}")

        confirmed = sum(1 for item in session.checklist_items if item.status == "confirmed")
        needs_clarification = sum(1 for item in session.checklist_items if item.status == "needs_clarification")
        lines.append(
            f"Подтвержденных пунктов: {confirmed}. Пунктов для уточнения: {needs_clarification}."
        )

        top_items = [
            item.item.strip()
            for item in session.checklist_items
            if item.item and item.status in {"confirmed", "needs_clarification"}
        ][:3]
        if top_items:
            lines.append("Основные пункты: " + "; ".join(top_items) + ".")

        text = " ".join(lines)
        text = text.replace("`", "").replace("*", "")
        return text[: self.settings.tts_max_chars].strip()

    async def synthesize_summary(self, session: SessionData) -> Tuple[bytes, str]:
        text = self.build_summary_text(session)
        if self.provider == "huggingface":
            try:
                return await self._synthesize_hf(text)
            except Exception:
                # Non-blocking fallback: playback still works even if HF endpoint is slow/down.
                return self._mock_wav(text)
        return self._mock_wav(text)

    async def _synthesize_hf(self, text: str) -> Tuple[bytes, str]:
        headers = {"Accept": "audio/wav"}
        if self.settings.huggingface_api_key:
            headers["Authorization"] = f"Bearer {self.settings.huggingface_api_key}"

        payload = {
            "inputs": text,
            "options": {"wait_for_model": True},
        }
        url = f"https://api-inference.huggingface.co/models/{self.settings.tts_model}"

        async with httpx.AsyncClient(timeout=self.settings.tts_timeout_seconds) as client:
            resp = await client.post(url, headers=headers, json=payload)

        content_type = (resp.headers.get("content-type") or "").lower()
        if resp.status_code >= 400 or "application/json" in content_type:
            detail = ""
            try:
                detail = json.dumps(resp.json(), ensure_ascii=False)
            except Exception:
                detail = resp.text[:400]
            raise RuntimeError(f"HuggingFace TTS error ({resp.status_code}): {detail}")

        if not resp.content:
            raise RuntimeError("HuggingFace TTS returned empty audio payload")
        return resp.content, resp.headers.get("content-type", "audio/wav")

    @staticmethod
    def _mock_wav(text: str) -> Tuple[bytes, str]:
        duration_seconds = max(1.0, min(6.0, len(text) / 55.0))
        sample_rate = 22050
        amplitude = 8000
        frequency = 440.0
        total_samples = int(duration_seconds * sample_rate)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            frames = bytearray()
            for i in range(total_samples):
                value = int(amplitude * math.sin(2 * math.pi * frequency * (i / sample_rate)))
                frames.extend(value.to_bytes(2, byteorder="little", signed=True))
            wav_file.writeframes(bytes(frames))

        return buffer.getvalue(), "audio/wav"
