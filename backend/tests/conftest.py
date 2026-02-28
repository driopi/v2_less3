import os

import pytest
from fastapi.testclient import TestClient

os.environ["WHISPER_MODE"] = "mock"
os.environ["PRELOAD_WHISPER_ON_STARTUP"] = "false"
os.environ["TTS_PROVIDER"] = "mock"
os.environ["TTS_MODEL"] = "facebook/mms-tts-rus"
os.environ["LLM_PROVIDER"] = "mock"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("HUGGINGFACE_API_KEY", None)
os.environ.pop("GEMINI_API_KEY", None)

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
