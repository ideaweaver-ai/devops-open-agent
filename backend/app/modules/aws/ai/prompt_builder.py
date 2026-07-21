"""AWS troubleshooting prompt builder."""

import json
from typing import Any

BASE_SYSTEM_PROMPT = """You are a Senior AWS Cloud Engineer and SRE performing infrastructure troubleshooting.

Analyze the provided evidence and produce a precise root cause analysis with actionable recommendations.

CORE RULES:
- Use ONLY provided evidence — do not guess or invent values.
- Never use placeholder resource IDs, CIDRs, account IDs, regions, or usernames.
- Every AWS CLI command must use resource IDs, ports, protocols, and regions copied from the evidence JSON.
- Cite resource IDs, ports, principals, timestamps, and source IPs from evidence.
- Never reference EC2 instances or security groups unless they appear in discovery_assessment or ec2_findings.instances.
- Never reference Lambda functions unless they appear in lambda_findings.functions.
- Never reference S3 buckets unless they appear in s3_findings.buckets.
- If ec2_findings.status is no_instances_discovered, report that no instances exist in the selected region — do not claim an instance is stopped or healthy.
- If lambda_findings.status is no_functions_discovered, report that no Lambda functions exist in the selected region.
- If s3_findings.status is no_buckets_discovered, report that no S3 buckets exist in the selected region.
- If referenced_but_not_discovered lists resource IDs, tell the user to verify region/account selection.
- Confidence above 70 requires findings backed by discovered resources, not user query text alone.
- If finding_summary is empty and discovery found no issues, say no issues were found in scope — do not invent incidents.
- Put AWS CLI commands in kubectl_commands field for schema compatibility.
- Safe by default — flag destructive commands for human review.
- Keep the full JSON response concise: suggested_fix under 1200 characters, at most 5 kubectl_commands, at most 8 evidence items.
- Do not wrap the JSON in markdown code fences.

When observability_data findings from Prometheus or Grafana are present:
- Cite them explicitly in evidence with source "observability".
- Prefer correlating host/EC2 metrics (CPU, load, memory) and Grafana dashboards/annotations with CloudWatch and EC2 findings.
- Do NOT invent metric values, dashboard titles, or log lines that are not in observability_data.
- If findings is empty or observability is disabled, do not invent Prometheus/Grafana evidence.

SUGGESTED_FIX REQUIREMENTS:
- suggested_fix must be detailed, numbered, and grounded entirely in finding_summary and evidence sections.
- Address each finding category present in the evidence (do not assume EC2 or security issues exist unless evidence shows them).
- For each security group rule in evidence: include SG ID, port/protocol, CIDR, attribution if present, and exact remediation approach.
- For each stopped instance in evidence: include attribution if present, restart decision, and verification steps.
- Do not repeat boilerplate unrelated to the collected findings.
- kubectl_commands must mirror commands described in suggested_fix.
- validation_steps and prevention_recommendation must relate to findings actually detected in this investigation.

Evidence source values: ec2, lambda, s3, vpc, security_groups, load_balancers, cloudwatch, cloudtrail, config, topology, auto_scaling, observability

Respond with valid JSON only using this exact schema:
{
  "root_cause": "string",
  "summary": "string",
  "evidence": [{"source": "...", "detail": "string"}],
  "suggested_fix": "string",
  "kubectl_commands": ["string"],
  "validation_steps": ["string"],
  "prevention_recommendation": "string",
  "confidence_score": 0,
  "confidence_reason": "string",
  "needs_more_data": false,
  "additional_data_needed": []
}"""

ISSUE_TYPE_INSTRUCTIONS: dict[str, str] = {
    "full_scan": """TROUBLESHOOTING MODE: Full infrastructure scan.
- Review finding_summary and report ALL issues ranked by severity (critical → high → medium).
- Include security exposures, EC2 state issues, Lambda function health, S3 bucket posture, load balancer health, CloudWatch alarms, observability (Prometheus/Grafana) findings, and recent changes.
- Do not ignore security group rules (including HTTP/80 and HTTPS/443 on 0.0.0.0/0).
- If multiple unrelated issues exist, summarize each clearly in root_cause.
- When observability_data reports host CPU/load pressure, cite it even if CloudWatch averages look low.""",
    "security": """TROUBLESHOOTING MODE: Security & exposure.
- Focus on security_findings.internet_exposed_ingress_rules — every 0.0.0.0/0 and ::/0 rule MUST be reported.
- Include HTTP (80), HTTPS (443), SSH (22), and all-traffic rules.
- Correlate with cloudtrail_findings.attribution_by_security_group and security_group_change_events.
- AWS Console changes often appear as ModifySecurityGroupRules (not only AuthorizeSecurityGroupIngress) — use both.
- For each exposed rule, state WHO added it, WHEN, and source IP when CloudTrail provides attribution.
- Recommend least-privilege fixes with specific revoke/modify commands.""",
    "ec2_availability": """TROUBLESHOOTING MODE: EC2 availability.
- Focus on stopped/unhealthy instances and incident_attribution.
- Answer WHO stopped each instance, WHEN, and FROM WHERE using CloudTrail.
- Correlate CloudWatch instance_activity timeline.
- Still mention critical security issues if present, but EC2 availability is primary.""",
    "lambda": """TROUBLESHOOTING MODE: Lambda functions.
- Focus ONLY on lambda_findings and cloudwatch_findings.lambda_invocations.
- Do NOT report EC2, S3, or security group findings unless the user query explicitly mentions them.
- Report invocation timeouts from CloudWatch Logs (Status: timeout) and Errors/Duration metrics.
- Report inactive or failed functions, disabled event source mappings, and VPC/security group attachment issues.
- Still mention critical security issues if present, but Lambda health is primary.""",
    "s3": """TROUBLESHOOTING MODE: S3 storage.
- Focus on s3_findings.problematic_buckets — public policies, missing public access blocks, encryption, and versioning gaps.
- Report logging gaps and Lambda/SQS/SNS notification triggers when present.
- Recommend least-privilege bucket policies and encryption defaults with specific bucket names from evidence.
- Keep suggested_fix short: one numbered step per bucket, max 6 steps total.
- Still mention critical security issues if present, but S3 posture is primary.""",
    "network": """TROUBLESHOOTING MODE: Network & connectivity.
- Focus on VPC topology, security group rules affecting connectivity, and internet exposure.
- Analyze whether traffic can reach instances (SG ingress/egress, subnets, route implications from topology).""",
    "load_balancer": """TROUBLESHOOTING MODE: Load balancers.
- Focus on unhealthy targets, inactive load balancers, and target group health reasons.
- Correlate with EC2 instance state if targets are instances.""",
    "performance": """TROUBLESHOOTING MODE: Performance & monitoring.
- Prioritize observability_data (Prometheus / Grafana) when present — host CPU, load, memory, and dashboard hits are first-class evidence.
- Correlate Prometheus host metrics (e.g. node_cpu / load / Alloy instance labels) with CloudWatch CPUUtilization for the same EC2 instances.
- Do NOT conclude "no high CPU" from CloudWatch alone if observability_data shows elevated host CPU or load.
- Also review CloudWatch alarms in ALARM state and instance metric activity.
- Identify metric anomalies, idle vs active instances, and threshold breaches.""",
    "change_audit": """TROUBLESHOOTING MODE: Change audit & attribution.
- Focus on CloudTrail events: who changed what, when, from which IP.
- Include tag changes (CreateTags/DeleteTags) with tag key/value from tag_change_events and ec2_findings.instances.tags.
- Include security group changes, instance state changes, and AWS Config recent_changes.
- Build a timeline of relevant API activity.""",
}


FOCUSED_PROMPT_SECTIONS: dict[str, list[str]] = {
    "s3": [
        "discovery_assessment",
        "finding_summary",
        "s3_findings",
        "security_findings",
        "observability_data",
        "account",
    ],
    "lambda": [
        "discovery_assessment",
        "finding_summary",
        "lambda_findings",
        "cloudwatch_findings",
        "observability_data",
        "account",
    ],
    "ec2_availability": [
        "discovery_assessment",
        "finding_summary",
        "ec2_findings",
        "incident_attribution",
        "cloudtrail_findings",
        "cloudwatch_findings",
        "observability_data",
        "account",
    ],
    "load_balancer": [
        "discovery_assessment",
        "finding_summary",
        "load_balancer_findings",
        "ec2_findings",
        "observability_data",
        "account",
    ],
    "network": [
        "discovery_assessment",
        "finding_summary",
        "network_findings",
        "security_findings",
        "observability_data",
        "account",
    ],
    "security": [
        "discovery_assessment",
        "finding_summary",
        "security_findings",
        "cloudtrail_findings",
        "observability_data",
        "account",
    ],
    "performance": [
        "discovery_assessment",
        "finding_summary",
        "observability_data",
        "cloudwatch_findings",
        "ec2_findings",
        "account",
    ],
    "change_audit": [
        "discovery_assessment",
        "finding_summary",
        "cloudtrail_findings",
        "config_findings",
        "ec2_findings",
        "observability_data",
        "account",
    ],
}


class AwsPromptBuilder:
    """Build LLM prompts from AWS investigation context."""

    def build_messages(self, context: dict[str, Any]) -> list[dict[str, str]]:
        issue_type = context.get("troubleshooting_focus", {}).get("issue_type", "full_scan")
        mode_instructions = ISSUE_TYPE_INSTRUCTIONS.get(
            issue_type,
            ISSUE_TYPE_INSTRUCTIONS["full_scan"],
        )
        system_prompt = f"{BASE_SYSTEM_PROMPT}\n\n{mode_instructions}"
        user_prompt = self._build_user_prompt(context)
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _build_user_prompt(self, context: dict[str, Any]) -> str:
        focus = context.get("troubleshooting_focus", {})
        issue_type = focus.get("issue_type", "full_scan")
        section_keys = FOCUSED_PROMPT_SECTIONS.get(issue_type)
        sections = [
            "Analyze the AWS evidence below according to the troubleshooting mode in the system prompt.",
            "",
        ]

        for title, payload in self._prompt_sections(context, section_keys):
            sections.extend(
                [
                    f"## {title}",
                    json.dumps(payload, indent=2),
                    "",
                ]
            )

        # Always include Prometheus/Grafana evidence when collected, even if
        # a focused issue type omitted the section historically.
        observability = context.get("observability_data") or {}
        obs_findings = observability.get("findings") or []
        if obs_findings and (
            not section_keys or "observability_data" not in section_keys
        ):
            sections.extend(
                [
                    "## Observability Data (Prometheus / Grafana)",
                    json.dumps(observability, indent=2),
                    "",
                ]
            )

        rag_context = context.get("rag_context") or {}
        if rag_context.get("matches"):
            sections.extend(
                [
                    "## Similar Past Investigations (RAG)",
                    json.dumps(rag_context, indent=2),
                    "",
                    "Use these prior investigations as supporting context — note recurring root "
                    "causes and remediations that worked before, but ground the final diagnosis "
                    "in the current evidence.",
                    "",
                ]
            )

        if focus.get("query"):
            sections.extend(
                [
                    "## User-Reported Problem",
                    focus["query"],
                    "",
                    "Address the user-reported problem directly while grounding answers in evidence.",
                    "",
                ]
            )

        sections.append(
            "Return JSON only. Base every recommendation on the evidence above — no placeholders or assumed resources."
        )
        return "\n".join(sections)

    def _prompt_sections(
        self,
        context: dict[str, Any],
        section_keys: list[str] | None,
    ) -> list[tuple[str, Any]]:
        all_sections: list[tuple[str, Any]] = [
            ("Discovery Assessment (READ FIRST — defines what was actually found)", context.get("discovery_assessment", {})),
            ("Troubleshooting Focus", context.get("troubleshooting_focus", {})),
            ("Finding Summary (ALL detected issues — prioritize these)", context.get("finding_summary", {})),
            ("Security Findings", context.get("security_findings", {})),
            ("EC2 Findings", context.get("ec2_findings", {})),
            ("Lambda Findings", context.get("lambda_findings", {})),
            ("S3 Findings", context.get("s3_findings", {})),
            ("Incident Attribution (EC2 stop/start)", context.get("incident_attribution", {})),
            ("CloudTrail Findings", context.get("cloudtrail_findings", {})),
            ("CloudWatch Findings", context.get("cloudwatch_findings", {})),
            ("Network Findings", context.get("network_findings", {})),
            ("Load Balancer Findings", context.get("load_balancer_findings", {})),
            ("Auto Scaling Findings", context.get("auto_scaling_findings", {})),
            ("AWS Config Findings", context.get("config_findings", {})),
            ("Observability Data (Prometheus / Grafana)", context.get("observability_data", {})),
            ("MCP Server Context", context.get("mcp_enrichment", {})),
            (
                "Account & Resource Counts",
                {
                    "account": context.get("account", {}),
                    "resource_counts": context.get("resource_counts", {}),
                },
            ),
        ]

        if not section_keys:
            return all_sections

        key_to_section = {
            "discovery_assessment": all_sections[0],
            "finding_summary": all_sections[2],
            "security_findings": all_sections[3],
            "ec2_findings": all_sections[4],
            "lambda_findings": all_sections[5],
            "s3_findings": all_sections[6],
            "incident_attribution": all_sections[7],
            "cloudtrail_findings": all_sections[8],
            "cloudwatch_findings": all_sections[9],
            "network_findings": all_sections[10],
            "load_balancer_findings": all_sections[11],
            "auto_scaling_findings": all_sections[12],
            "config_findings": all_sections[13],
            "observability_data": all_sections[14],
            "mcp_enrichment": all_sections[15],
            "account": all_sections[16],
        }

        selected: list[tuple[str, Any]] = [all_sections[1]]
        for key in section_keys:
            section = key_to_section.get(key)
            if section and section not in selected:
                selected.append(section)
        return selected
