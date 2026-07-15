"""LLM analyzer for security scan results."""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

from app.ai.llm_factory import LLMProviderFactory
from app.ai.providers.exceptions import LLMProviderError
from app.core.config import Settings, get_settings
from app.modules.security.ai.prompt_builder import SecurityPromptBuilder


class SecurityAnalyzer:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.prompt_builder = SecurityPromptBuilder()

    async def analyze_scan(
        self,
        scan_results: dict[str, Any],
        scan_type: str,
    ) -> dict[str, Any]:
        messages = self.prompt_builder.build_messages(scan_results, scan_type)
        provider = LLMProviderFactory.create(settings=self.settings)
        provider_name = self.settings.llm_provider

        try:
            raw = await provider.generate(messages, temperature=0.1)
            payload = self._extract_json(raw)
            analysis_md = payload.get("analysis_markdown") or ""
            if len(analysis_md) < 200:
                analysis_md = self._build_fallback_report(payload, raw)
            return {
                "ai_analysis": analysis_md,
                "llm_provider": provider_name,
                "priority_findings": payload.get("priority_findings", []),
                "remediation_plan": payload.get("remediation_plan", []),
                "security_posture": payload.get("security_posture", "unknown"),
                "executive_summary": payload.get("executive_summary", ""),
            }
        except LLMProviderError:
            logger.exception("Security LLM analysis failed")
            raise
        except Exception:
            logger.exception("Unexpected security analysis failure")
            raw_text = locals().get("raw") or "n/a"
            return {
                "ai_analysis": (
                    "## Security Analysis\n\n"
                    "Unable to parse structured analysis from the LLM. "
                    f"Raw output:\n\n{raw_text[:4000]}"
                ),
                "llm_provider": provider_name,
                "priority_findings": [],
                "remediation_plan": [],
                "security_posture": "unknown",
                "executive_summary": "Analysis returned unstructured output.",
            }

    @staticmethod
    def _build_fallback_report(payload: dict[str, Any], raw: str) -> str:
        """Build a markdown report from structured fields when analysis_markdown is too short."""
        parts: list[str] = []

        posture = payload.get("security_posture", "unknown").replace("_", " ").title()
        parts.append(f"## Security Posture: {posture}\n")

        summary = payload.get("executive_summary")
        if summary:
            parts.append(f"## Executive Summary\n\n{summary}\n")

        findings = payload.get("priority_findings") or []
        if findings:
            parts.append("## Priority Findings\n")
            for f in findings:
                sev = f.get("severity", "?")
                fid = f.get("id", "?")
                title = f.get("title", "")
                reason = f.get("reason", "")
                fix = f.get("remediation", "")
                parts.append(f"### [{sev}] {fid}: {title}\n")
                if reason:
                    parts.append(f"**Why prioritized:** {reason}\n")
                if fix:
                    parts.append(f"**Remediation:** {fix}\n")

        plan = payload.get("remediation_plan") or []
        if plan:
            parts.append("## Remediation Plan\n")
            for step in plan:
                prio = step.get("priority", "?")
                action = step.get("action", "")
                cmds = step.get("commands") or []
                parts.append(f"- **[{prio}]** {action}")
                for cmd in cmds:
                    parts.append(f"  ```\n  {cmd}\n  ```")
            parts.append("")

        if not parts:
            return f"## Security Analysis\n\n{raw[:4000]}"

        return "\n".join(parts)

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
