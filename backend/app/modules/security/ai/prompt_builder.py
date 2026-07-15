"""Prompt builder for security scan analysis."""

from __future__ import annotations

from typing import Any


SYSTEM_PROMPT = """You are a senior application security engineer reviewing Trivy scan results.

Rules:
- Prioritize findings by exploitability and blast radius, not just CVSS score.
- Group related vulnerabilities (e.g. same base image layer or same library).
- Suggest concrete remediation steps: upgrade commands, Dockerfile changes, K8s manifest patches.
- Flag any critical/high findings that are actively exploited (known KEV).
- Provide an overall security posture summary (healthy, needs attention, at risk, critical).
- Do not invent CVE IDs or package names that are not in the scan results.
- The analysis_markdown field MUST contain a full, detailed markdown report — not a placeholder or description of sections.
"""

SEVERITY_PRIORITY = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}


class SecurityPromptBuilder:
    def build_messages(
        self,
        scan_results: dict[str, Any],
        scan_type: str,
    ) -> list[dict[str, str]]:
        vulns = scan_results.get("vulnerabilities") or []
        misconfigs = scan_results.get("misconfigurations") or []
        summary = scan_results.get("summary") or {}
        target = scan_results.get("target") or "unknown"

        sorted_vulns = sorted(
            vulns,
            key=lambda v: SEVERITY_PRIORITY.get(v.get("severity", "UNKNOWN"), 5),
        )

        vuln_lines = []
        for v in sorted_vulns[:40]:
            fixed = v.get("fixed_version") or "no fix"
            vuln_lines.append(
                f"- [{v.get('severity','?')}] {v.get('vulnerability_id','?')}: "
                f"{v.get('pkg_name','?')} {v.get('installed_version','?')} -> {fixed} | "
                f"{v.get('title','')}"
            )

        misconfig_lines = []
        for m in misconfigs[:20]:
            misconfig_lines.append(
                f"- [{m.get('severity','?')}] {m.get('id','?')}: {m.get('title','')} | "
                f"resource={m.get('resource','?')} | resolution: {m.get('resolution','')}"
            )

        user_prompt = f"""Analyze the following Trivy {scan_type} scan results for target: {target}

Severity summary: {summary}
Total vulnerabilities: {len(vulns)}
Total misconfigurations: {len(misconfigs)}

Top vulnerabilities (sorted by severity, showing {len(vuln_lines)} of {len(vulns)}):
{chr(10).join(vuln_lines) if vuln_lines else "(none)"}

Misconfigurations (showing {len(misconfig_lines)} of {len(misconfigs)}):
{chr(10).join(misconfig_lines) if misconfig_lines else "(none)"}

Respond with a JSON object (no markdown fences around the JSON). Every field must contain real content, not placeholders.

Required JSON shape:
{{
  "security_posture": "healthy" or "needs_attention" or "at_risk" or "critical",
  "executive_summary": "Write 2-4 sentences summarizing the security state for leadership.",
  "priority_findings": [
    {{
      "severity": "CRITICAL or HIGH or MEDIUM or LOW",
      "id": "the actual CVE or misconfig ID from the scan",
      "title": "short title",
      "reason": "why this is prioritized",
      "remediation": "specific fix steps"
    }}
  ],
  "remediation_plan": [
    {{
      "priority": "immediate or short_term or long_term",
      "action": "what to do",
      "commands": ["optional advisory command"]
    }}
  ],
  "analysis_markdown": "Write a FULL detailed markdown report here. Include these sections with real content:\\n## Executive Summary\\n(2-4 sentences)\\n## Critical Findings\\n(list the most important vulnerabilities with CVE IDs)\\n## Remediation Plan\\n(prioritized steps)\\n## Security Posture Assessment\\n(overall assessment)"
}}
"""
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
