import os

import pytest
from fastapi.testclient import TestClient

os.environ["WHISPER_MODE"] = "mock"
os.environ["PRELOAD_WHISPER_ON_STARTUP"] = "false"
os.environ.pop("ANTHROPIC_API_KEY", None)

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
