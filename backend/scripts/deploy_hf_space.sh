#!/usr/bin/env bash
set -euo pipefail

if [ -z "${HF_SPACE_ID:-}" ]; then
  echo "Set HF_SPACE_ID like: username/space-name"
  exit 1
fi

HF_BIN="${HF_BIN:-/Users/andrey/Library/Python/3.9/bin/hf}"

cd "$(dirname "$0")/.."

if ! "$HF_BIN" auth whoami >/dev/null 2>&1; then
  echo "Hugging Face CLI is not authenticated. Run: $HF_BIN auth login"
  exit 1
fi

"$HF_BIN" repo create "$HF_SPACE_ID" --repo-type space --space-sdk docker || true
"$HF_BIN" upload "$HF_SPACE_ID" . \
  --repo-type space \
  --exclude ".env" \
  --exclude ".venv/*" \
  --exclude "__pycache__/*"

echo "Uploaded backend to https://huggingface.co/spaces/$HF_SPACE_ID"
