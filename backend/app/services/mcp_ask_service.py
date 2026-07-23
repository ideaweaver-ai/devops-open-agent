"""Answer user questions by calling MCP server tools."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from loguru import logger

from app.ai.json_utils import extract_json_object
from app.ai.llm_factory import LLMProviderFactory
from app.ai.providers.exceptions import LLMProviderError
from app.ai.usage import UsageTracker
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.integrations.mcp.client import McpClient, McpClientError
from app.services.llm_usage_service import persist_usage_session
from app.services.mcp_settings_service import McpSettingsService
from app.storage.factory import get_llm_usage_store

MAX_TOOL_ROUNDS = 3
MAX_TOOL_CATALOG = 40


class McpAskService:
    def __init__(
        self,
        settings_service: McpSettingsService | None = None,
        client: McpClient | None = None,
    ) -> None:
        self.settings_service = settings_service or McpSettingsService()
        self.client = client or McpClient()
        self.settings = get_settings()

    async def ask(self, question: str, user_id: UUID) -> dict[str, Any]:
        trimmed = question.strip()
        if not trimmed:
            raise ValueError("Question is required")

        async with SessionLocal() as session:
            server_url, api_key = await self.settings_service.resolve_connection(
                session,
                user_id,
                agent_type="kubernetes",
                require_enabled=False,
            )

        if not server_url:
            raise McpClientError("Configure an MCP server URL before asking questions.")

        tools_used: list[dict[str, Any]] = []
        tool_results: list[dict[str, Any]] = []
        usage_store = get_llm_usage_store()
        await usage_store.initialize()

        with UsageTracker.session(
            scope_type="mcp_ask",
            scope_id=str(user_id),
            user_id=str(user_id),
            agent_type="mcp",
            default_call_kind="mcp_ask",
        ) as usage_session:

            async def run_session(mcp_session) -> str:
                tools_result = await mcp_session.list_tools()
                catalog = self._build_tool_catalog(tools_result.tools)

                for round_index in range(MAX_TOOL_ROUNDS):
                    plan = await self._plan_next_step(trimmed, catalog, tool_results)
                    action = plan.get("action", "answer")

                    if action == "answer":
                        answer = (plan.get("answer") or "").strip()
                        if answer:
                            return answer
                        break

                    tool_name = (plan.get("tool_name") or "").strip()
                    arguments = plan.get("arguments") or {}
                    if not tool_name:
                        break

                    if not any(tool["name"] == tool_name for tool in catalog):
                        tool_results.append(
                            {
                                "tool_name": tool_name,
                                "error": f"Unknown tool: {tool_name}",
                            }
                        )
                        continue

                    try:
                        result = await mcp_session.call_tool(tool_name, arguments)
                        summary = self.client.format_tool_result(result)[:4000]
                        tools_used.append({"name": tool_name, "arguments": arguments})
                        tool_results.append(
                            {
                                "tool_name": tool_name,
                                "arguments": arguments,
                                "result": summary,
                            }
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("MCP tool call failed | tool={} error={}", tool_name, exc)
                        tool_results.append(
                            {
                                "tool_name": tool_name,
                                "arguments": arguments,
                                "error": str(exc),
                            }
                        )

                return await self._synthesize_answer(trimmed, tool_results)

            answer = await self.client.execute(
                server_url,
                api_key,
                run_session,
            )
            await persist_usage_session(usage_store, usage_session)

        return {
            "answer": answer,
            "tools_used": tools_used,
            "tool_results": tool_results,
            "llm_usage": usage_session.summary_dict(),
        }

    def _build_tool_catalog(self, tools: list[Any]) -> list[dict[str, Any]]:
        catalog: list[dict[str, Any]] = []
        for tool in tools[:MAX_TOOL_CATALOG]:
            catalog.append(
                {
                    "name": tool.name,
                    "description": (tool.description or "").strip(),
                    "input_schema": getattr(tool, "inputSchema", None) or {},
                }
            )
        return catalog

    async def _plan_next_step(
        self,
        question: str,
        catalog: list[dict[str, Any]],
        tool_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        system_prompt = (
            "You are an MCP assistant. Choose whether to call one MCP tool or answer directly.\n"
            "Respond with JSON only using this schema:\n"
            '{"action":"call_tool"|"answer","tool_name":string|null,'
            '"arguments":object,"answer":string|null}\n'
            "Use call_tool when external data is required. Use answer when you can respond "
            "without another tool or when prior tool results are enough."
        )
        user_content = (
            f"User question:\n{question}\n\n"
            f"Available MCP tools:\n{json.dumps(catalog, indent=2)}"
        )
        if tool_results:
            user_content += f"\n\nPrior tool results:\n{json.dumps(tool_results, indent=2)}"

        raw = await self._generate_json(system_prompt, user_content)
        return extract_json_object(raw)

    async def _synthesize_answer(
        self,
        question: str,
        tool_results: list[dict[str, Any]],
    ) -> str:
        if not tool_results:
            return (
                "I could not gather data from your MCP server for that question. "
                "Try rephrasing or pick a more specific GitHub action."
            )

        system_prompt = (
            "Answer the user's question using MCP tool results. Be concise and factual.\n"
            "Format as clean markdown: short intro sentence, then a bullet list with "
            "`- **#123**: title (by author)` for pull requests.\n"
            'Respond with JSON only: {"answer":"..."}'
        )
        user_content = (
            f"User question:\n{question}\n\n"
            f"MCP tool results:\n{json.dumps(tool_results, indent=2)}"
        )
        raw = await self._generate_json(system_prompt, user_content)
        payload = extract_json_object(raw)
        answer = (payload.get("answer") or "").strip()
        return answer or "No answer could be generated from the MCP tool results."

    async def _generate_json(self, system_prompt: str, user_content: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        try:
            provider = LLMProviderFactory.create(settings=self.settings)
            return await provider.generate(messages, temperature=0.1)
        except LLMProviderError as exc:
            raise McpClientError(f"LLM request failed: {exc}") from exc


mcp_ask_service = McpAskService()
