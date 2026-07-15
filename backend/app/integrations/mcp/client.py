"""MCP client for Streamable HTTP servers."""

from __future__ import annotations

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


class McpClientError(Exception):
    """Raised when MCP server communication fails."""


def _auth_headers(api_key: str | None) -> dict[str, str]:
    if not api_key or not api_key.strip():
        return {}
    key = api_key.strip()
    if key.lower().startswith("bearer "):
        return {"Authorization": key}
    return {"Authorization": f"Bearer {key}"}


def _format_probe_error(exc: BaseException) -> str:
    if isinstance(exc, McpClientError):
        return str(exc)
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in {401, 403}:
            return "MCP server rejected the API key (check Authorization Bearer token)."
        body = ""
        try:
            body = exc.response.text[:300].strip()
        except Exception:
            pass
        detail = f"MCP server returned HTTP {status}."
        if body:
            detail += f" Response: {body}"
        return detail
    if isinstance(exc, ExceptionGroup):
        for sub in exc.exceptions:
            return _format_probe_error(sub)
    return str(exc) or exc.__class__.__name__


class McpClient:
    """Connect to a remote MCP server and list tools/resources."""

    def __init__(self, timeout_seconds: float = 30.0, read_timeout_seconds: float = 120.0) -> None:
        self.timeout = httpx.Timeout(timeout_seconds, read=read_timeout_seconds)

    async def probe_server(self, server_url: str, api_key: str | None = None) -> dict:
        """Initialize a session and return available tools and resources."""
        url = server_url.strip()
        if not url:
            raise McpClientError("MCP server URL is required")

        headers = _auth_headers(api_key)
        try:
            async with httpx.AsyncClient(
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True,
            ) as http_client:
                async with streamable_http_client(url=url, http_client=http_client) as transport:
                    read, write = transport[0], transport[1]
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools_result = await session.list_tools()
                        resources: list[dict[str, str]] = []
                        try:
                            resources_result = await session.list_resources()
                            resources = [
                                {
                                    "uri": resource.uri,
                                    "name": resource.name,
                                    "description": (resource.description or "").strip(),
                                }
                                for resource in resources_result.resources
                            ]
                        except Exception:
                            resources = []
        except McpClientError:
            raise
        except Exception as exc:
            raise McpClientError(_format_probe_error(exc)) from exc

        tools = [
            {
                "name": tool.name,
                "description": (tool.description or "").strip(),
            }
            for tool in tools_result.tools
        ]
        return {
            "tools": tools,
            "resources": resources,
            "tool_count": len(tools),
            "resource_count": len(resources),
        }

    async def execute(
        self,
        server_url: str,
        api_key: str | None,
        handler,
    ):
        """Run a callback with an initialized MCP session."""
        url = server_url.strip()
        if not url:
            raise McpClientError("MCP server URL is required")

        headers = _auth_headers(api_key)
        try:
            async with httpx.AsyncClient(
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True,
            ) as http_client:
                async with streamable_http_client(url=url, http_client=http_client) as transport:
                    read, write = transport[0], transport[1]
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        return await handler(session)
        except McpClientError:
            raise
        except Exception as exc:
            raise McpClientError(_format_probe_error(exc)) from exc

    @staticmethod
    def format_tool_result(result) -> str:
        if getattr(result, "isError", False):
            return "Tool returned an error."
        chunks: list[str] = []
        for block in getattr(result, "content", []) or []:
            text = getattr(block, "text", None)
            if text:
                chunks.append(text)
        if chunks:
            return "\n".join(chunks)
        return str(result)
