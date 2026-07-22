"""LLM-as-a-Judge: secondary AI verification of a primary diagnosis."""

import json
import re
from typing import Any

from loguru import logger
from pydantic import ValidationError

from app.ai.json_utils import extract_json_object
from app.ai.llm_factory import LLMProviderFactory
from app.ai.providers.exceptions import LLMProviderError
from app.core.config import Settings, get_settings
from app.models.diagnosis import DiagnosisResult, JudgeVerdict

_VALID_VERDICTS = {"agree", "partially_agree", "disagree"}

_SYSTEM_PROMPT = """\
You are an expert SRE peer-reviewer acting as a judge for an AI-generated \
Kubernetes diagnosis. You will receive:

1. The ORIGINAL DIAGNOSIS produced by a primary AI.
2. The RAW INVESTIGATION EVIDENCE collected from the cluster.

Your job is to evaluate the diagnosis on five axes:

A. **Factual consistency** — Does every claim in the diagnosis match the evidence?
B. **Evidence grounding** — Is the root cause actually supported by the cited evidence sources?
C. **Command safety** — Are the kubectl commands safe to run (no destructive deletes, \
no broad-scope operations without namespace scoping)?
D. **Completeness** — Did the diagnosis miss any signals present in the evidence?
E. **Actionability** — Is the suggested fix specific enough to act on?

Respond with ONLY a JSON object (no markdown fences, no extra text) matching this schema:

{
  "verdict": "agree | partially_agree | disagree",
  "confidence_score": <0-100>,
  "reasoning": "<concise paragraph explaining overall assessment>",
  "factual_issues": ["<issue 1>", ...],
  "missed_evidence": ["<missed signal 1>", ...],
  "command_safety_concerns": ["<concern 1>", ...],
  "suggested_improvements": ["<improvement 1>", ...]
}

Rules:
- "agree" = diagnosis is accurate, complete, and safe.
- "partially_agree" = mostly correct but has gaps or minor issues.
- "disagree" = significant factual errors or dangerous recommendations.
- Empty arrays are fine when no issues are found for that category.
- Be specific — cite pod names, event reasons, or log lines when relevant.
- Do NOT invent evidence that is not present in the investigation data.
"""


def _summarize_diagnosis(diagnosis: DiagnosisResult) -> str:
    """Serialize the primary diagnosis into a compact text block for the judge."""
    parts = [
        f"Root Cause: {diagnosis.root_cause}",
        f"Summary: {diagnosis.summary}",
        f"Suggested Fix: {diagnosis.suggested_fix}",
        f"Confidence: {diagnosis.confidence_score}% — {diagnosis.confidence_reason}",
    ]
    if diagnosis.evidence:
        evidence_lines = [f"  - [{e.source}] {e.detail}" for e in diagnosis.evidence]
        parts.append("Evidence:\n" + "\n".join(evidence_lines))
    if diagnosis.kubectl_commands:
        parts.append("kubectl Commands:\n" + "\n".join(f"  $ {c}" for c in diagnosis.kubectl_commands))
    if diagnosis.validation_steps:
        parts.append("Validation Steps:\n" + "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(diagnosis.validation_steps)))
    if diagnosis.prevention_recommendation:
        parts.append(f"Prevention: {diagnosis.prevention_recommendation}")
    if diagnosis.issue_diagnoses:
        for idx, issue in enumerate(diagnosis.issue_diagnoses, 1):
            parts.append(
                f"\n--- Per-Pod Issue {idx}: {issue.pod} ({issue.namespace}) ---\n"
                f"  Status: {issue.status} | Reason: {issue.reason}\n"
                f"  Root Cause: {issue.root_cause}\n"
                f"  Fix: {issue.suggested_fix}"
            )
    return "\n\n".join(parts)


def _summarize_evidence(evidence_context: dict[str, Any]) -> str:
    """Create a compact text summary of the raw investigation evidence."""
    sections: list[str] = []

    investigation = evidence_context.get("investigation", {})
    pods = investigation.get("pods", {})
    if pods.get("problematic_pods"):
        lines = []
        for p in pods["problematic_pods"]:
            lines.append(f"  - {p.get('name', '?')} ns={p.get('namespace')} "
                         f"status={p.get('status')} reason={p.get('reason')}")
        sections.append("Problematic Pods:\n" + "\n".join(lines))

    logs = investigation.get("logs", {})
    if logs.get("logs"):
        for log_entry in logs["logs"][:5]:
            pod_name = log_entry.get("pod", "unknown")
            log_lines = log_entry.get("lines", [])
            excerpt = log_lines[-10:] if log_lines else []
            if excerpt:
                sections.append(f"Logs ({pod_name}):\n" + "\n".join(f"  {l}" for l in excerpt))

    events = investigation.get("events", {})
    if events.get("findings"):
        lines = []
        for e in events["findings"][:10]:
            lines.append(f"  - [{e.get('type', '?')}] {e.get('reason', '?')}: {e.get('message', '')}")
        sections.append("Events:\n" + "\n".join(lines))

    deployments = investigation.get("deployments", {})
    if deployments.get("issues"):
        lines = [f"  - {d}" for d in deployments["issues"]]
        sections.append("Deployment Issues:\n" + "\n".join(lines))

    network = investigation.get("network", {})
    if network.get("issues"):
        lines = [f"  - {n}" for n in network["issues"]]
        sections.append("Network Issues:\n" + "\n".join(lines))

    if not sections:
        sections.append("No significant findings in raw evidence.")

    return "\n\n".join(sections)


class DiagnosisJudge:
    """Run a secondary LLM to verify a primary diagnosis."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def evaluate(
        self,
        diagnosis: DiagnosisResult,
        evidence: dict[str, Any],
        judge_provider: str | None = None,
        judge_model: str | None = None,
    ) -> JudgeVerdict:
        messages = self._build_prompt(diagnosis, evidence)
        resolved_provider = self._resolve_provider_name(judge_provider)
        try:
            provider = self._create_provider(resolved_provider, judge_model)
            raw_response = await provider.generate(messages, temperature=0.0)
            verdict = self._parse_verdict(raw_response)
            provider_label = resolved_provider
            if judge_model:
                provider_label = f"{resolved_provider}/{judge_model}"
            verdict.llm_provider = provider_label
            logger.info(
                "Judge verdict generated | provider={} verdict={} confidence={}",
                provider_label,
                verdict.verdict,
                verdict.confidence_score,
            )
            return verdict
        except LLMProviderError as exc:
            logger.error("Judge LLM call failed | error={}", exc)
            return self._fallback_verdict(str(exc))
        except Exception as exc:
            logger.exception("Unexpected judge failure")
            return self._fallback_verdict(str(exc))

    def _build_prompt(
        self,
        diagnosis: DiagnosisResult,
        evidence: dict[str, Any],
    ) -> list[dict[str, str]]:
        diagnosis_text = _summarize_diagnosis(diagnosis)
        evidence_text = _summarize_evidence(evidence)
        user_content = (
            "## PRIMARY DIAGNOSIS\n\n"
            f"{diagnosis_text}\n\n"
            "## RAW INVESTIGATION EVIDENCE\n\n"
            f"{evidence_text}"
        )
        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    def _parse_verdict(self, raw_response: str) -> JudgeVerdict:
        payload = extract_json_object(raw_response)
        payload = self._normalize_payload(payload)
        try:
            return JudgeVerdict.model_validate(payload)
        except ValidationError as exc:
            logger.warning("Judge JSON did not match schema, recovering | error={}", exc)
            recovered = self._recover_payload(payload)
            return JudgeVerdict.model_validate(recovered)

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        verdict = str(payload.get("verdict", "")).lower().replace(" ", "_")
        if verdict not in _VALID_VERDICTS:
            if "disagree" in verdict:
                verdict = "disagree"
            elif "partial" in verdict:
                verdict = "partially_agree"
            else:
                verdict = "agree"
        payload["verdict"] = verdict
        return payload

    def _recover_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "verdict": payload.get("verdict", "partially_agree"),
            "confidence_score": int(payload.get("confidence_score", 50) or 50),
            "reasoning": str(payload.get("reasoning", "Judge output could not be fully parsed.")),
            "factual_issues": payload.get("factual_issues") or [],
            "missed_evidence": payload.get("missed_evidence") or [],
            "command_safety_concerns": payload.get("command_safety_concerns") or [],
            "suggested_improvements": payload.get("suggested_improvements") or [],
        }

    def _create_provider(
        self,
        resolved_provider: str,
        request_model: str | None = None,
    ):
        settings = self.settings
        model = request_model or self._resolve_model(resolved_provider)
        if model:
            settings = self._settings_with_model_override(resolved_provider, model)

        return LLMProviderFactory.create(
            provider_name=resolved_provider,
            settings=settings,
        )

    def _resolve_provider_name(self, request_override: str | None = None) -> str:
        if request_override:
            return request_override.lower()
        return self.settings.judge_llm_provider or self.settings.llm_provider

    def _resolve_model(self, provider_name: str) -> str:
        model_map = {
            "openai": self.settings.judge_openai_model,
            "anthropic": self.settings.judge_anthropic_model,
            "openrouter": self.settings.judge_openrouter_model,
            "gemini": self.settings.judge_gemini_model,
            "ollama": self.settings.judge_ollama_model,
            "bedrock": self.settings.judge_bedrock_model,
        }
        return model_map.get(provider_name, "")

    def _settings_with_model_override(self, provider_name: str, model: str) -> Settings:
        """Return a copy of settings with the specific provider's model overridden."""
        overrides = {f"{provider_name}_model": model}
        return self.settings.model_copy(update=overrides)

    @staticmethod
    def _fallback_verdict(error: str | None = None) -> JudgeVerdict:
        return JudgeVerdict(
            verdict="partially_agree",
            confidence_score=0,
            reasoning="Unable to generate judge verdict due to an LLM error.",
            llm_error=error,
        )
