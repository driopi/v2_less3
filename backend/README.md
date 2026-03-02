---
title: AI Checklist Agent Voice
emoji: "🎙️"
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# Backend (FastAPI + LangGraph)

## Что реализовано
- FastAPI API для сессий интервью (3 раунда × 3 вопроса)
- LangGraph workflow для генерации вопросов и финального чеклиста
- LLM генерация через Gemini 2.5 Flash (с fallback на mock)
- Локальная транскрипция через `openai/whisper-small`
- Озвучка итогов с легкой TTS-моделью (`facebook/mms-tts-rus`) через HF Inference API + mock fallback
- Карточка речевого портрета (стабильность, скрытое напряжение, триггеры, рекомендация) по 9 транскриптам
- Превью транскрипции и финальная генерация Markdown
- Опциональный MCP bridge для Tavily/Hugging Face tools
- Preflight тесты без запуска реальной Whisper (`mock` режим)

## Запуск локально
```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 7860
```

## Быстрый preflight до реальной модели
> Важно: запуск реальной модели в Hugging Face Spaces может занимать 3-5 минут.
> Сначала гоняем все тесты в mock-режиме, чтобы не тратить эти минуты на каждый фикс.

```bash
cd backend
./scripts/preflight.sh
```

## Реальная проверка Whisper
```bash
cd backend
export WHISPER_MODE=local
uvicorn app.main:app --reload --port 7860
```

## Реальная проверка TTS (оптимизированный режим)
```bash
cd backend
export TTS_PROVIDER=auto
export TTS_MODEL=facebook/mms-tts-rus
export HUGGINGFACE_API_KEY=hf_...
uvicorn app.main:app --reload --port 7860
```

## Hugging Face Spaces (Docker)
1. Создайте Docker Space.
2. Загрузите `backend/` как содержимое Space.
3. Добавьте secrets: `GEMINI_API_KEY`, `TAVILY_API_KEY`, `HUGGINGFACE_API_KEY` (опционально).
4. Проверьте `/health`.

CLI-скрипт автозагрузки:
```bash
cd backend
HF_SPACE_ID=username/space-name ./scripts/deploy_hf_space.sh
```

## API
- `POST /api/session/start`
- `GET /api/session/{id}`
- `POST /api/session/transcribe`
- `POST /api/session/{id}/submit`
- `GET /api/session/{id}/results`
- `GET /api/session/{id}/download`
- `GET /api/session/{id}/summary-audio`
- `GET /health`

Поддерживается два формата передачи аудио:
- `multipart/form-data` (прод)
- `application/json` с `audio_base64` / `audio_base64_files` (preflight и CI)
