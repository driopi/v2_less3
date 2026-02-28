#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export WHISPER_MODE=mock
export PRELOAD_WHISPER_ON_STARTUP=false
export TTS_PROVIDER=mock
export LLM_PROVIDER=mock
unset GEMINI_API_KEY
unset ANTHROPIC_API_KEY
unset HUGGINGFACE_API_KEY

printf "[preflight] Running API flow tests without real Whisper...\n"
python3 -m unittest tests/test_preflight_unittest.py -v

printf "\n[preflight] OK. Real model not started, flow is validated.\n"
printf "[preflight] Next: run with WHISPER_MODE=local for real transcription tests.\n"
