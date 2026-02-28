# MCP setup (Tavily + Hugging Face)

Установленные пакеты:
- `tavily-mcp`
- `huggingface-mcp-server`

## Локальный запуск серверов
```bash
cd mcp
cp .env.example .env
```

Tavily (stdio):
```bash
cd mcp
TAVILY_API_KEY=... npx tavily-mcp
```

Hugging Face (stdio):
```bash
cd mcp
HUGGINGFACE_API_KEY=... npx huggingface-mcp-server --transport stdio --api-key "$HUGGINGFACE_API_KEY"
```

## Подключение в backend LangGraph
В `backend/.env` включите:
```bash
ENABLE_MCP_TOOLS=true
MCP_TAVILY_COMMAND=npx -y tavily-mcp
MCP_HUGGINGFACE_COMMAND=npx -y huggingface-mcp-server --transport stdio --api-key $HUGGINGFACE_API_KEY
TAVILY_API_KEY=...
HUGGINGFACE_API_KEY=...
```

Альтернатива для Tavily: используйте удаленный URL `MCP_TAVILY_URL=https://mcp.tavily.com/mcp/?tavilyApiKey=...`.
