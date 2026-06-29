"""Format AI recommendations for PagerDuty Events API v2."""

from __future__ import annotations

from typing import Any

from app.models.diagnosis import DiagnosisResult

_AGENT_LABELS = {
    "kubernetes": "Kubernetes Debugging Agent",
    "aws": "AWS DevOps Agent",
    "cloud_cost": "Cloud Cost Detector",
    "pr_reviewer": "PR Reviewer",
}

_PR_RISK_SEVERITY = {
    "critical": "critical",
    "high": "error",
    "medium": "warning",
    "low": "info",
    "unknown": "warning",
}


def _truncate(text: str, limit: int = 1024) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def _investigation_severity(diagnosis: DiagnosisResult) -> str:
    score = diagnosis.confidence_score or 0
    if score >= 80:
        return "error"
    if score >= 50:
        return "warning"
    return "info"


def format_diagnosis_event(
    *,
    routing_key: str,
    agent_type: str,
    scope_label: str,
    investigation_id: str,
    diagnosis: DiagnosisResult,
    app_url: str = "",
) -> dict[str, Any]:
    """Build PagerDuty trigger event for an investigation diagnosis."""
    agent_label = _AGENT_LABELS.get(agent_type, agent_type.replace("_", " ").title())
    summary = _truncate(
        f"[{agent_label}] {scope_label}: {diagnosis.root_cause}",
        1024,
    )
    custom_details: dict[str, Any] = {
        "agent": agent_label,
        "scope": scope_label,
        "investigation_id": investigation_id,
        "confidence_score": diagnosis.confidence_score,
        "root_cause": diagnosis.root_cause,
        "summary": diagnosis.summary,
    }
    if diagnosis.suggested_fix:
        custom_details["suggested_fix"] = diagnosis.suggested_fix
    if diagnosis.prevention_recommendation:
        custom_details["prevention"] = diagnosis.prevention_recommendation
    if diagnosis.validation_steps:
        custom_details["validation_steps"] = diagnosis.validation_steps[:10]
    if app_url:
        custom_details["investigation_url"] = app_url

    return {
        "routing_key": routing_key,
        "event_action": "trigger",
        "dedup_key": f"devops-open-agent:investigation:{investigation_id}",
        "payload": {
            "summary": summary,
            "severity": _investigation_severity(diagnosis),
            "source": "devops-open-agent",
            "component": agent_type,
            "group": scope_label,
            "custom_details": custom_details,
        },
    }


def format_pr_review_event(
    *,
    routing_key: str,
    owner: str,
    repository: str,
    pull_request_number: int,
    pull_request_title: str,
    overall_risk: str,
    final_recommendation: str,
    findings_count: int,
    review_id: str,
    app_url: str = "",
) -> dict[str, Any]:
    """Build PagerDuty trigger event for a PR review recommendation."""
    repo_label = f"{owner}/{repository}"
    severity = _PR_RISK_SEVERITY.get((overall_risk or "").lower(), "warning")
    summary = _truncate(
        f"[PR Review] {repo_label}#{pull_request_number}: {final_recommendation}",
        1024,
    )
    custom_details: dict[str, Any] = {
        "repository": repo_label,
        "pull_request_number": pull_request_number,
        "pull_request_title": pull_request_title,
        "overall_risk": overall_risk,
        "findings_count": findings_count,
        "final_recommendation": final_recommendation,
        "review_id": review_id,
    }
    if app_url:
        custom_details["review_url"] = app_url

    return {
        "routing_key": routing_key,
        "event_action": "trigger",
        "dedup_key": f"devops-open-agent:pr:{review_id}",
        "payload": {
            "summary": summary,
            "severity": severity,
            "source": "devops-open-agent",
            "component": "pr_reviewer",
            "group": repo_label,
            "custom_details": custom_details,
        },
    }


def format_test_event(*, routing_key: str) -> dict[str, Any]:
    return {
        "routing_key": routing_key,
        "event_action": "trigger",
        "dedup_key": "devops-open-agent:test",
        "payload": {
            "summary": "DevOps Open Agent — PagerDuty integration test",
            "severity": "info",
            "source": "devops-open-agent",
            "component": "integrations",
            "custom_details": {
                "message": (
                    "PagerDuty integration is working. "
                    "AI recommendations will be sent as incidents when investigations complete."
                ),
            },
        },
    }
