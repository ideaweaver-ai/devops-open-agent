"""Shared-LLM analyzer for Linux performance evidence."""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

from app.ai.llm_factory import LLMProviderFactory
from app.ai.providers.exceptions import LLMProviderError
from app.core.config import Settings, get_settings
from app.modules.performance.ai.prompt_builder import PerformancePromptBuilder


class PerformanceAnalyzer:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.prompt_builder = PerformancePromptBuilder()

    async def analyze_host(self, host: str, evidence: str) -> dict[str, Any]:
        messages = self.prompt_builder.build_messages(host, evidence)
        provider = LLMProviderFactory.create(settings=self.settings)
        try:
            raw = await provider.generate(messages, temperature=0.1)
            payload = self._extract_json(raw)
            return self._normalize(host, payload, raw)
        except LLMProviderError:
            logger.exception("Performance LLM analysis failed | host={}", host)
            raise
        except Exception:
            logger.exception("Unexpected performance analysis failure | host={}", host)
            raw_fallback = locals().get("raw") or "n/a"
            return {
                "summary": f"Analysis returned unstructured output for {host}.",
                "severity": "medium",
                "findings": [],
                "root_causes": [],
                "recommendations": [],
                "analysis_markdown": (
                    f"## {host}\n\nUnable to parse structured analysis. "
                    f"Raw model output:\n\n{raw_fallback}"
                ),
            }

    async def summarize_fleet(self, host_summaries: list[dict[str, str]]) -> str:
        if not host_summaries:
            return "No hosts were analyzed."
        messages = self.prompt_builder.build_fleet_summary_messages(host_summaries)
        provider = LLMProviderFactory.create(settings=self.settings)
        try:
            return (await provider.generate(messages, temperature=0.2)).strip()
        except Exception:
            logger.exception("Fleet summary generation failed")
            severe = [
                item
                for item in host_summaries
                if (item.get("severity") or "").lower() in {"high", "critical"}
            ]
            if severe:
                names = ", ".join(item["host"] for item in severe[:8])
                return f"Completed host debugging. Elevated severity on: {names}."
            return f"Completed performance debugging for {len(host_summaries)} host(s)."

    def _extract_json(self, raw_response: str) -> dict[str, Any]:
        text = raw_response.strip()
        if text.startswith("```"):
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return parsed
        raise ValueError("Model response was not valid JSON")

    def _normalize(self, host: str, payload: dict[str, Any], raw: str) -> dict[str, Any]:
        severity = str(payload.get("severity") or "medium").lower()
        if severity not in {"low", "medium", "high", "critical"}:
            severity = "medium"
        markdown = payload.get("analysis_markdown")
        if not isinstance(markdown, str) or not markdown.strip():
            markdown = self._fallback_markdown(host, payload, raw)
        return {
            "summary": str(payload.get("summary") or f"Performance analysis for {host}"),
            "severity": severity,
            "findings": payload.get("findings") if isinstance(payload.get("findings"), list) else [],
            "root_causes": payload.get("root_causes")
            if isinstance(payload.get("root_causes"), list)
            else [],
            "recommendations": payload.get("recommendations")
            if isinstance(payload.get("recommendations"), list)
            else [],
            "analysis_markdown": markdown,
        }

    @staticmethod
    def _fallback_markdown(host: str, payload: dict[str, Any], raw: str) -> str:
        summary = payload.get("summary") or "See findings below."
        return f"## {host}\n\n{summary}\n\n### Raw\n\n{raw[:4000]}"
