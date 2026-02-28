from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from app.config import Settings


class MCPToolProvider:
    """Optional MCP bridge for Tavily and Hugging Face tools."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _server_config(self) -> Dict[str, Dict[str, Any]]:
        config: Dict[str, Dict[str, Any]] = {}
        if self.settings.mcp_tavily_url:
            config["tavily"] = {
                "transport": "streamable_http",
                "url": self.settings.mcp_tavily_url,
            }
        elif self.settings.mcp_tavily_command:
            command, args = self.settings.split_command(self.settings.mcp_tavily_command)
            config["tavily"] = {
                "transport": "stdio",
                "command": command,
                "args": args,
                "env": {
                    "TAVILY_API_KEY": self.settings.tavily_api_key or "",
                },
            }

        if self.settings.mcp_huggingface_url:
            config["huggingface"] = {
                "transport": "streamable_http",
                "url": self.settings.mcp_huggingface_url,
            }
        elif self.settings.mcp_huggingface_command:
            command, args = self.settings.split_command(self.settings.mcp_huggingface_command)
            config["huggingface"] = {
                "transport": "stdio",
                "command": command,
                "args": args,
                "env": {
                    "HUGGINGFACE_API_KEY": self.settings.huggingface_api_key or "",
                },
            }
        return config

    async def get_tools(self) -> List[Any]:
        if not self.settings.enable_mcp_tools:
            return []

        servers = self._server_config()
        if not servers:
            return []

        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient

            client = MultiServerMCPClient(servers)
            # MCP servers can be slow/unavailable; avoid blocking the full request.
            return await asyncio.wait_for(client.get_tools(), timeout=8.0)
        except Exception:
            # MCP is optional; if unavailable we continue without external tools.
            return []
