# Frontend (Next.js 15)

## Запуск локально
```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

`NEXT_PUBLIC_API_URL` должен указывать на backend (локально: `http://localhost:7860`, прод: `https://<space>.hf.space`).

## Deploy на Vercel
1. Импортируйте `frontend/` как отдельный проект.
2. Добавьте env:
   - `NEXT_PUBLIC_API_URL=https://<your-space>.hf.space`
3. Выполните `vercel --prod`.

Или используйте скрипт:
```bash
cd frontend
./scripts/deploy_vercel.sh
```
