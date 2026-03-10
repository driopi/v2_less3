from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.graph import ChecklistGraphService
from app.config import get_settings
from app.routers.health import router as health_router
from app.routers.session import router as session_router
from app.services.llm import LLMService
from app.services.mcp import MCPToolProvider
from app.services.portrait import PortraitService
from app.services.transcription import TranscriptionService
from app.services.tts import TTSService
from app.storage.job_store import JobStore
from app.storage.session_store import SessionStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    transcription_service = TranscriptionService(settings)
    if settings.preload_whisper_on_startup:
        transcription_service.preload()

    mcp_provider = MCPToolProvider(settings)
    llm_service = LLMService(settings, mcp_provider=mcp_provider)
    portrait_service = PortraitService(settings)
    tts_service = TTSService(settings)

    app.state.settings = settings
    app.state.transcription_service = transcription_service
    app.state.llm_service = llm_service
    app.state.portrait_service = portrait_service
    app.state.tts_service = tts_service
    app.state.mcp_provider = mcp_provider
    app.state.graph_service = ChecklistGraphService(llm_service, portrait_service=portrait_service)
    app.state.session_store = SessionStore()
    app.state.job_store = JobStore()

    yield


app = FastAPI(title="AI Checklist Agent API", version="0.1.0", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-TTS-Source"],
)

app.include_router(health_router)
app.include_router(session_router)
