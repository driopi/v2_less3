# AI Checklist Agent (Voice, 9 Questions)

Монорепозиторий:
- `backend/`: FastAPI + LangGraph + Whisper + MCP bridge
- `frontend/`: Next.js 15 UI (голосовые ответы, 3 раунда, результаты)
- `mcp/`: локальные пакеты и конфиг для Tavily/Hugging Face MCP

## Что уже сделано
- Новый проект создан с архитектурой из вашего плана.
- Реализован агент с 3 раундами по 3 вопроса (итого 9).
- Реализованы API для старта сессии, транскрипции, отправки ответов, получения и скачивания результата.
- Добавлена генерация итогового `.md` чеклиста.
- Добавлена поддержка MCP-инструментов для Tavily/Hugging Face (опционально через env).
- Установлены skills: `speech`, `transcribe`, `vercel-deploy`.
- Установлены MCP пакеты: `tavily-mcp`, `huggingface-mcp-server`.

## Ключевой акцент на тестировании до реального Whisper
Запуск Hugging Face Spaces с реальной Whisper обычно занимает 3-5 минут. Чтобы не терять время:

1. Сначала запускать preflight (`mock` режим):
```bash
cd backend
./scripts/preflight.sh
```
2. Только после успешного preflight переключаться на `WHISPER_MODE=local`.
3. Только после локальной проверки отправлять в Hugging Face Space.

## Быстрый запуск
Backend:
```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
./scripts/preflight.sh
uvicorn app.main:app --reload --port 7860
```

Frontend:
```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

## Deploy
- Hugging Face Spaces: деплойте содержимое `backend/` в Docker Space.
- Vercel: деплойте `frontend/` с `NEXT_PUBLIC_API_URL=https://<space>.hf.space`.
- Скрипты:
  - `backend/scripts/deploy_hf_space.sh`
  - `frontend/scripts/deploy_vercel.sh`

## Что еще нужно от вас
- `GEMINI_API_KEY` (LLM для генерации вопросов/summary/checklist)
- `TAVILY_API_KEY` (если включаете Tavily MCP)
- `HUGGINGFACE_API_KEY` (для HF MCP/инференса)
- Аккаунты и логин в Hugging Face + Vercel CLI
