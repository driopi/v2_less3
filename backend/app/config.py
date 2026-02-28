import os
import shlex
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass
class Settings:
    environment: str
    allowed_origins: List[str]

    llm_provider: str
    gemini_api_key: Optional[str]
    anthropic_api_key: Optional[str]
    llm_model: str

    whisper_model: str
    whisper_mode: str
    preload_whisper_on_startup: bool
    max_audio_duration_seconds: int

    enable_mcp_tools: bool
    mcp_tavily_url: Optional[str]
    mcp_huggingface_url: Optional[str]
    mcp_tavily_command: Optional[str]
    mcp_huggingface_command: Optional[str]
    tavily_api_key: Optional[str]
    huggingface_api_key: Optional[str]

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            environment=os.getenv("ENVIRONMENT", "development"),
            allowed_origins=_env_list("ALLOWED_ORIGINS", ["*"]),
            llm_provider=os.getenv("LLM_PROVIDER", "gemini"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            llm_model=os.getenv("LLM_MODEL", "gemini-2.5-flash"),
            whisper_model=os.getenv("WHISPER_MODEL", "openai/whisper-small"),
            whisper_mode=os.getenv("WHISPER_MODE", "local"),
            preload_whisper_on_startup=_env_bool("PRELOAD_WHISPER_ON_STARTUP", False),
            max_audio_duration_seconds=int(os.getenv("MAX_AUDIO_DURATION_SECONDS", "120")),
            enable_mcp_tools=_env_bool("ENABLE_MCP_TOOLS", False),
            mcp_tavily_url=os.getenv("MCP_TAVILY_URL"),
            mcp_huggingface_url=os.getenv("MCP_HUGGINGFACE_URL"),
            mcp_tavily_command=os.getenv("MCP_TAVILY_COMMAND"),
            mcp_huggingface_command=os.getenv("MCP_HUGGINGFACE_COMMAND"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            huggingface_api_key=os.getenv("HUGGINGFACE_API_KEY"),
        )

    @staticmethod
    def split_command(command: str) -> Tuple[str, List[str]]:
        parts = shlex.split(command)
        if not parts:
            raise ValueError("Empty command")
        return parts[0], parts[1:]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
