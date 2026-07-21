"""Kubernetes troubleshooting prompt builder."""

import json
from typing import Any

SYSTEM_PROMPT = """You are a Senior Kubernetes SRE.

Your job is to analyze structured Kubernetes investigation evidence and produce a precise root cause analysis.

Do not guess.
Use only the provided evidence.
If evidence is insufficient, say what additional data is needed.
Always include confidence score and evidence.

Recommendations must be:
- Practical
- Kubernetes-specific
- Beginner friendly
- Safe by default
- Evidence-driven

Do not suggest deleting production resources unless clearly framed as risky and requiring human approval.
Do not automatically execute any fix. Only recommend commands for human review.

When observability_data findings from Prometheus or Grafana are present:
- Cite them explicitly in evidence with source "observability".
- Prefer correlating metrics/logs/annotations with pod/event evidence.
- Do NOT invent metric values, CVEs, or log lines that are not in observability_data.
- If findings is empty or observability is disabled, do not invent metrics or external log evidence.

Confidence score guidelines:
- 90-100: Multiple evidence sources confirm the same cause.
- 70-89: Strong evidence but one or more signals missing.
- 40-69: Possible cause but incomplete evidence.
- 0-39: Insufficient evidence.

When multiple problematic pods are present:
- Treat each pod as a separate issue unless evidence proves they share one root cause.
- The root_cause field must explain every problematic pod, using numbered items if needed.
- Include at least one evidence item per problematic pod.
- The suggested_fix and kubectl_commands must address every problematic pod.

Respond with valid JSON only using this exact schema:
{
  "root_cause": "string",
  "summary": "string",
  "evidence": [
    {
      "source": "logs|events|pods|deployments|network|topology|observability|deployments",
      "detail": "string"
    }
  ],
  "suggested_fix": "string",
  "kubectl_commands": ["string"],
  "validation_steps": ["string"],
  "prevention_recommendation": "string",
  "confidence_score": 0,
  "confidence_reason": "string",
  "needs_more_data": false,
  "additional_data_needed": []
}"""


class PromptBuilder:
    """Build LLM prompts from investigation context."""

    def build_messages(self, context: dict[str, Any]) -> list[dict[str, str]]:
        user_prompt = self._build_user_prompt(context)
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    def _build_user_prompt(self, context: dict[str, Any]) -> str:
        sections = [
            "Analyze the following Kubernetes investigation evidence and produce a correlated root cause analysis.",
            "",
            "## Cluster Info",
            json.dumps(context.get("cluster_info", {}), indent=2),
            "",
            "## Pod Findings",
            json.dumps(context.get("pod_findings", {}), indent=2),
            "",
            "## Per-Pod Issues",
            json.dumps(context.get("per_pod_issues", {}), indent=2),
            "",
            "## Log Findings",
            json.dumps(context.get("log_findings", {}), indent=2),
            "",
            "## Event Findings",
            json.dumps(context.get("event_findings", {}), indent=2),
            "",
            "## Deployment Findings",
            json.dumps(context.get("deployment_findings", {}), indent=2),
            "",
            "## Network Findings",
            json.dumps(context.get("network_findings", {}), indent=2),
            "",
            "## Topology Relationships",
            json.dumps(context.get("topology_relationships", []), indent=2),
            "",
            "## Observability Data",
            json.dumps(context.get("observability_data", {}), indent=2),
            "",
            "## Deployment Correlation Data",
            json.dumps(context.get("deployment_correlation_data", {}), indent=2),
            "",
            "## MCP Server Context",
            json.dumps(context.get("mcp_enrichment", {}), indent=2),
            "",
            "## Similar Past Investigations (RAG)",
            json.dumps(context.get("rag_context", {}), indent=2),
            "",
            "## Resource Summary",
            json.dumps(context.get("resource_summary", {}), indent=2),
            "",
            "Correlate evidence across pods, logs, events, deployments, network, topology, and MCP tools when provided.",
            "When Similar Past Investigations (RAG) are provided, use them as supporting context: note recurring root causes and fixes that worked before, but always ground the final diagnosis in the current evidence.",
            "Do not produce a diagnosis based on logs alone when other evidence sources are available.",
            "If per_pod_issues.count is greater than 1, analyze and explain each pod independently.",
            "Cite at least one evidence item per problematic pod.",
            "Return JSON only.",
        ]
        return "\n".join(sections)
