"""Prompt builder for Linux performance analysis."""

from __future__ import annotations


SYSTEM_PROMPT = """You are a Linux performance engineer helping DevOps/SRE teams.
Analyze the collected host evidence and identify likely performance bottlenecks.

Rules:
- Only cite processes, PIDs, load values, memory, disk, and network facts that appear in the evidence.
- Do not invent resource IDs, PIDs, or sysctl values that are not supported by the evidence.
- Remediation must be advice only — never claim you executed kill, sysctl, or other changes.
- Prefer specific, actionable guidance (commands the operator can choose to run).
- If evidence is incomplete or SSH collected only partial data, say so and lower confidence.
- Respond with JSON only (no markdown fences) matching the schema described by the user.
"""


class PerformancePromptBuilder:
    def build_messages(self, host: str, evidence: str) -> list[dict[str, str]]:
        user_prompt = f"""Analyze Linux performance evidence for host: {host}

Evidence:
{evidence}

Return JSON with this shape:
{{
  "summary": "1-3 sentence overview of host health",
  "severity": "low" | "medium" | "high" | "critical",
  "findings": [
    {{
      "subsystem": "cpu|memory|disk|network|load|other",
      "process_name": "optional process name from evidence",
      "pid": "optional PID string from evidence",
      "observation": "what you observed",
      "impact": "why it matters"
    }}
  ],
  "root_causes": ["likely root cause 1", "..."],
  "recommendations": [
    {{
      "priority": "high|medium|low",
      "action": "what to do",
      "commands": ["optional advisory command", "..."]
    }}
  ],
  "analysis_markdown": "Markdown report for operators with sections: Summary, Findings, Root Causes, Recommended Next Steps"
}}
"""
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    def build_fleet_summary_messages(
        self,
        host_summaries: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        lines = []
        for item in host_summaries:
            lines.append(
                f"- {item.get('host')}: severity={item.get('severity') or 'n/a'}; "
                f"{item.get('summary') or item.get('error') or 'no summary'}"
            )
        body = "\n".join(lines) if lines else "(no host results)"
        return [
            {
                "role": "system",
                "content": (
                    "You summarize multi-host Linux performance debug results for SRE leads. "
                    "Be concise. Do not invent hosts. Respond with plain text (not JSON)."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Write a short overall summary (max 8 sentences) across these hosts, "
                    "highlighting the most severe issues and shared themes:\n\n"
                    f"{body}"
                ),
            },
        ]
