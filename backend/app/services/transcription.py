from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import tempfile

from app.config import Settings
from app.utils.audio import AudioConverter


class TranscriptionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._loaded = False
        self._pipeline = None

    def preload(self) -> None:
        if self.settings.whisper_mode == "local":
            self._pipeline = self._get_pipeline(self.settings.whisper_model)
            self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded or self.settings.whisper_mode == "mock"

    @staticmethod
    @lru_cache(maxsize=1)
    def _get_pipeline(model_name: str):
        from transformers import pipeline

        return pipeline(
            "automatic-speech-recognition",
            model=model_name,
            device="cpu",
        )

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        if self.settings.whisper_mode == "mock":
            size = len(audio_bytes)
            return f"[mock transcript] Получен аудио-ответ, размер {size} байт."

        suffix = Path(filename).suffix.lower()
        tmp_input_wav = None
        if suffix == ".wav":
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                tmp_input_wav = Path(f.name)
            wav_path = tmp_input_wav
        else:
            wav_path = AudioConverter.webm_to_wav(audio_bytes)

        try:
            if self._pipeline is None:
                self._pipeline = self._get_pipeline(self.settings.whisper_model)
                self._loaded = True

            result = self._pipeline(str(wav_path))
            return result["text"].strip()
        finally:
            if wav_path.exists():
                wav_path.unlink(missing_ok=True)
