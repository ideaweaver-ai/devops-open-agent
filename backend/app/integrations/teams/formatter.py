"""Format AI recommendations for Microsoft Teams MessageCards."""

from __future__ import annotations

from typing import Any

from app.models.diagnosis import DiagnosisResult

_AGENT_LABELS = {
    "kubernetes": "Kubernetes Debugging Agent",
    "aws": "AWS DevOps Agent",
    "cloud_cost": "Cloud Cost Detector",
    "pr_reviewer": "PR Reviewer",
}


def _truncate(text: str, limit: int = 2800) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def _facts(items: list[tuple[str, str]]) -> list[dict[str, str]]:
    return [{"name": name, "value": value} for name, value in items]


def _message_card(
    *,
    title: str,
    summary: str,
    facts: list[tuple[str, str]],
    sections: list[str],
    action_url: str = "",
    theme_color: str = "0078D4",
) -> dict[str, Any]:
    card: dict[str, Any] = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": theme_color,
        "summary": _truncate(summary, 500),
        "title": title,
        "sections": [
            {
                "facts": _facts(facts),
                "text": "\n\n".join(_truncate(section) for section in sections if section),
            }
        ],
    }
    if action_url:
        card["potentialAction"] = [
            {
                "@type": "OpenUri",
                "name": "View in DevOps Open Agent",
                "targets": [{"os": "default", "uri": action_url}],
            }
        ]
    return card


def format_diagnosis_teams_payload(
    *,
    agent_type: str,
    scope_label: str,
    investigation_id: str,
    diagnosis: DiagnosisResult,
    app_url: str = "",
) -> dict[str, Any]:
    agent_label = _AGENT_LABELS.get(agent_type, agent_type.replace("_", " ").title())
    facts = [
        ("Agent", agent_label),
        ("Scope", scope_label),
        ("Confidence", f"{diagnosis.confidence_score}%"),
        ("Investigation", investigation_id[:8]),
    ]
    sections = [
        f"**Root cause**\n{_truncate(diagnosis.root_cause)}",
        f"**Summary**\n{_truncate(diagnosis.summary)}",
    ]
    if diagnosis.suggested_fix:
        sections.append(f"**Suggested fix**\n{_truncate(diagnosis.suggested_fix)}")
    if diagnosis.prevention_recommendation:
        sections.append(f"**Prevention**\n{_truncate(diagnosis.prevention_recommendation)}")
    if diagnosis.validation_steps:
        steps = "\n".join(f"- {step}" for step in diagnosis.validation_steps[:5])
        sections.append(f"**Validation steps**\n{steps}")

    return _message_card(
        title="DevOps Open Agent — AI Recommendation",
        summary=f"{agent_label}: {diagnosis.root_cause}",
        facts=facts,
        sections=sections,
        action_url=app_url,
    )


def format_pr_review_teams_payload(
    *,
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
    repo_label = f"{owner}/{repository}"
    facts = [
        ("Repository", repo_label),
        ("Pull request", f"#{pull_request_number}"),
        ("Risk", overall_risk or "unknown"),
        ("Findings", str(findings_count)),
        ("Review", review_id[:8]),
    ]
    sections = [
        f"**Title**\n{_truncate(pull_request_title, 500)}",
        f"**Recommendation**\n{_truncate(final_recommendation)}",
    ]
    return _message_card(
        title="DevOps Open Agent — PR Review",
        summary=f"PR Review for {repo_label}#{pull_request_number}",
        facts=facts,
        sections=sections,
        action_url=app_url,
        theme_color="6264A7",
    )


def format_test_teams_payload() -> dict[str, Any]:
    return _message_card(
        title="DevOps Open Agent — Teams test",
        summary="Teams integration test",
        facts=[("Status", "Connected")],
        sections=[
            "Microsoft Teams integration is working. "
            "AI recommendations from DevOps Open Agent will be posted to this channel."
        ],
    )
