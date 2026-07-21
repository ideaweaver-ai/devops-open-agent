"""Build AI-ready context from AWS investigation evidence."""

from __future__ import annotations

from typing import Any

from app.modules.aws.ai.discovery_assessment import build_discovery_assessment
from app.modules.aws.ai.finding_rules import (
    SECURITY_EVENT_NAMES,
    SEVERITY_ORDER,
    analyze_security_groups,
)
from app.modules.aws.collectors.cloudtrail import STATE_CHANGE_EVENT_NAMES, TAG_EVENT_NAMES
from app.modules.aws.investigation_scope import finding_categories
from app.modules.aws.models import AwsInvestigationResponse

ACTIVITY_METRICS = {"CPUUtilization", "NetworkIn", "NetworkOut", "DiskReadOps", "DiskWriteOps"}


class AwsContextBuilder:
    """Transform AWS investigation payloads into compact LLM context."""

    MAX_CLOUDTRAIL_EVENTS = 40
    MAX_TOPOLOGY_RELATIONSHIPS = 60
    MAX_METRICS = 30

    def build(self, investigation: AwsInvestigationResponse | dict[str, Any]) -> dict[str, Any]:
        if isinstance(investigation, AwsInvestigationResponse):
            payload = investigation.model_dump(exclude={"diagnosis", "error"})
        else:
            payload = dict(investigation)
            payload.pop("diagnosis", None)
            payload.pop("error", None)

        resources = payload.get("resources", {})
        cloudwatch = payload.get("cloudwatch", {})
        cloudtrail = payload.get("cloudtrail", {})
        aws_config = payload.get("aws_config", {})
        topology = payload.get("topology", {})

        ec2_instances = resources.get("ec2_instances", [])
        lambda_functions = resources.get("lambda_functions", [])
        s3_buckets = resources.get("s3_buckets", [])
        security_groups = resources.get("security_groups", [])
        target_groups = resources.get("target_groups", [])
        load_balancers = resources.get("load_balancers", [])

        ec2_findings = self._build_ec2_findings(ec2_instances)
        lambda_findings = self._build_lambda_findings(
            lambda_functions,
            cloudwatch.get("lambda_metrics") or [],
        )
        s3_findings = self._build_s3_findings(s3_buckets)
        cloudtrail_findings = self._build_cloudtrail_findings(cloudtrail, ec2_instances)
        cloudwatch_findings = self._build_cloudwatch_findings(cloudwatch, ec2_instances)
        security_findings = self._build_security_findings(security_groups, cloudtrail_findings)
        network_findings = self._build_network_findings(resources.get("vpcs", []), security_findings)
        load_balancer_findings = self._build_load_balancer_findings(load_balancers, target_groups)
        auto_scaling_findings = self._build_asg_findings(resources.get("auto_scaling_groups", []))
        incident_attribution = self._build_incident_attribution(
            ec2_instances,
            cloudtrail_findings,
            cloudwatch_findings,
        )

        investigation_ctx = payload.get("investigation", {})
        troubleshooting_focus = {
            "issue_type": investigation_ctx.get("issue_type", "full_scan"),
            "query": investigation_ctx.get("query"),
        }
        discovery_assessment = build_discovery_assessment(
            investigation_ctx,
            ec2_instances,
            security_groups,
            troubleshooting_focus,
            cloudtrail_findings,
        )

        finding_summary = self._build_finding_summary(
            ec2_findings=ec2_findings,
            lambda_findings=lambda_findings,
            s3_findings=s3_findings,
            security_findings=security_findings,
            load_balancer_findings=load_balancer_findings,
            auto_scaling_findings=auto_scaling_findings,
            cloudwatch_findings=cloudwatch_findings,
            cloudtrail_findings=cloudtrail_findings,
            incident_attribution=incident_attribution,
            discovery_assessment=discovery_assessment,
            issue_type=troubleshooting_focus.get("issue_type", "full_scan"),
            observability=payload.get("observability") or {},
        )

        return {
            "troubleshooting_focus": troubleshooting_focus,
            "discovery_assessment": discovery_assessment,
            "account": payload.get("account", {}),
            "investigation": investigation_ctx,
            "finding_summary": finding_summary,
            "ec2_findings": ec2_findings,
            "lambda_findings": lambda_findings,
            "s3_findings": s3_findings,
            "security_findings": security_findings,
            "incident_attribution": incident_attribution,
            "network_findings": network_findings,
            "load_balancer_findings": load_balancer_findings,
            "auto_scaling_findings": auto_scaling_findings,
            "cloudwatch_findings": cloudwatch_findings,
            "cloudtrail_findings": cloudtrail_findings,
            "config_findings": self._build_config_findings(aws_config),
            "topology_relationships": (topology.get("relationships") or [])[
                : self.MAX_TOPOLOGY_RELATIONSHIPS
            ],
            "topology_summary": {
                "node_count": len(topology.get("graph_nodes") or []),
                "relationship_count": len(topology.get("relationships") or []),
                "kinds": self._summarize_topology_kinds(topology.get("graph_nodes") or []),
            },
            "resource_counts": investigation_ctx.get("resource_counts", {}),
            "mcp_enrichment": payload.get("mcp_enrichment", {}),
            "rag_context": payload.get("rag_context", {}),
            "observability_data": payload.get("observability", {}),
        }

    def _build_ec2_findings(self, instances: list[dict[str, Any]]) -> dict[str, Any]:
        problematic: list[dict[str, Any]] = []
        for instance in instances:
            state = str(instance.get("state") or "").lower()
            status_checks = instance.get("status_checks") or {}
            instance_status = str(status_checks.get("instance_status") or "").lower()
            system_status = str(status_checks.get("system_status") or "").lower()

            issues: list[str] = []
            if state and state not in {"running", "pending"}:
                issues.append(f"instance state is {state}")
            if instance_status and instance_status != "ok":
                issues.append(f"instance status check: {instance_status}")
            if system_status and system_status != "ok":
                issues.append(f"system status check: {system_status}")

            if issues:
                problematic.append(
                    {
                        "instance_id": instance.get("instance_id"),
                        "name": instance.get("name"),
                        "instance_type": instance.get("instance_type"),
                        "private_ip": instance.get("private_ip"),
                        "public_ip": instance.get("public_ip"),
                        "vpc_id": instance.get("vpc_id"),
                        "subnet_id": instance.get("subnet_id"),
                        "security_groups": instance.get("security_groups", []),
                        "state": instance.get("state"),
                        "state_transition_reason": instance.get("state_transition_reason"),
                        "launch_time": instance.get("launch_time"),
                        "auto_scaling_group": instance.get("auto_scaling_group"),
                        "issues": issues,
                        "requires_attribution": state in {"stopped", "stopping", "terminated", "shutting-down"},
                    }
                )

        return {
            "total_instances": len(instances),
            "instances": [
                {
                    "instance_id": instance.get("instance_id"),
                    "name": instance.get("name"),
                    "state": instance.get("state"),
                    "state_transition_reason": instance.get("state_transition_reason"),
                    "tags": instance.get("tags") or {},
                }
                for instance in instances
            ],
            "problematic_instances": problematic,
            "healthy": len(problematic) == 0 if instances else None,
            "status": (
                "no_instances_discovered"
                if not instances
                else "healthy" if not problematic else "issues_found"
            ),
        }

    def _build_lambda_findings(
        self,
        functions: list[dict[str, Any]],
        lambda_metrics: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        metrics_by_name = {
            str(item.get("function_name")): item for item in (lambda_metrics or [])
        }
        problematic: list[dict[str, Any]] = []
        for function in functions:
            issues: list[str] = []
            state = str(function.get("state") or "").lower()
            last_update_status = str(function.get("last_update_status") or "").lower()
            metrics = metrics_by_name.get(str(function.get("function_name")), {})

            if state and state != "active":
                issues.append(f"function state is {function.get('state')}")
            if last_update_status and last_update_status not in {"successful", ""}:
                issues.append(f"last update status is {function.get('last_update_status')}")
            for event_source in function.get("event_sources") or []:
                event_state = str(event_source.get("state") or "").lower()
                if event_state and event_state not in {"enabled", "creating", "updating"}:
                    issues.append(
                        f"event source {event_source.get('event_source_arn')} is {event_source.get('state')}"
                    )

            errors = int(metrics.get("errors") or 0)
            if errors > 0:
                issues.append(f"{errors} invocation error(s) in CloudWatch lookback window")

            timeout_log_events = int(metrics.get("timeout_log_events") or 0)
            if timeout_log_events > 0:
                issues.append(
                    f"{timeout_log_events} timeout event(s) in CloudWatch Logs "
                    f"(REPORT Status: timeout / Task timed out)"
                )
            elif metrics.get("duration_at_timeout"):
                timeout_sec = function.get("timeout") or metrics.get("configured_timeout_sec")
                max_duration = metrics.get("max_duration_ms")
                issues.append(
                    f"invocation duration reached configured timeout "
                    f"({max_duration}ms max vs {timeout_sec}s timeout)"
                )

            throttles = int(metrics.get("throttles") or 0)
            if throttles > 0:
                issues.append(f"{throttles} throttle event(s) in CloudWatch lookback window")

            if issues:
                problematic.append(
                    {
                        "function_name": function.get("function_name"),
                        "function_arn": function.get("function_arn"),
                        "runtime": function.get("runtime"),
                        "timeout": function.get("timeout"),
                        "vpc_id": function.get("vpc_id"),
                        "invocation_metrics": metrics,
                        "issues": issues,
                    }
                )

        return {
            "total_functions": len(functions),
            "functions": [
                {
                    "function_name": function.get("function_name"),
                    "function_arn": function.get("function_arn"),
                    "runtime": function.get("runtime"),
                    "state": function.get("state"),
                    "timeout": function.get("timeout"),
                    "vpc_id": function.get("vpc_id"),
                    "environment_keys": function.get("environment_keys") or [],
                    "event_source_count": len(function.get("event_sources") or []),
                    "invocation_metrics": metrics_by_name.get(str(function.get("function_name")), {}),
                }
                for function in functions
            ],
            "problematic_functions": problematic,
            "healthy": len(problematic) == 0 if functions else None,
            "status": (
                "no_functions_discovered"
                if not functions
                else "healthy" if not problematic else "issues_found"
            ),
        }

    def _build_s3_findings(self, buckets: list[dict[str, Any]]) -> dict[str, Any]:
        problematic: list[dict[str, Any]] = []
        for bucket in buckets:
            issues: list[str] = []
            if bucket.get("policy_is_public") is True:
                issues.append("bucket policy is public")
            public_access_block = bucket.get("public_access_block") or {}
            if not public_access_block:
                issues.append("public access block is not configured")
            elif not all(
                public_access_block.get(key) is True
                for key in (
                    "block_public_acls",
                    "ignore_public_acls",
                    "block_public_policy",
                    "restrict_public_buckets",
                )
            ):
                issues.append("public access block is not fully enabled")
            if bucket.get("encryption_enabled") is False:
                issues.append("default encryption is not enabled")
            if bucket.get("versioning_status") not in {"Enabled", "enabled"}:
                issues.append("versioning is not enabled")

            if issues:
                problematic.append(
                    {
                        "bucket_name": bucket.get("bucket_name"),
                        "region": bucket.get("region"),
                        "issues": issues,
                        "policy_is_public": bucket.get("policy_is_public"),
                        "encryption_enabled": bucket.get("encryption_enabled"),
                    }
                )

        return {
            "total_buckets": len(buckets),
            "buckets": [
                {
                    "bucket_name": bucket.get("bucket_name"),
                    "region": bucket.get("region"),
                    "policy_is_public": bucket.get("policy_is_public"),
                    "encryption_enabled": bucket.get("encryption_enabled"),
                    "versioning_status": bucket.get("versioning_status"),
                    "logging_enabled": bucket.get("logging_enabled"),
                    "notification_count": len(bucket.get("notifications") or []),
                }
                for bucket in buckets
            ],
            "problematic_buckets": problematic,
            "healthy": len(problematic) == 0 if buckets else None,
            "status": (
                "no_buckets_discovered"
                if not buckets
                else "healthy" if not problematic else "issues_found"
            ),
        }

    def _build_security_findings(
        self,
        security_groups: list[dict[str, Any]],
        cloudtrail_findings: dict[str, Any],
    ) -> dict[str, Any]:
        internet_exposed, permissive_egress = analyze_security_groups(security_groups)
        sg_changes = cloudtrail_findings.get("security_group_change_events") or []
        sg_attribution = cloudtrail_findings.get("attribution_by_security_group") or {}

        enriched_rules = []
        for rule in internet_exposed:
            group_id = str(rule.get("security_group_id") or "")
            attribution = sg_attribution.get(group_id, {})
            latest_change = attribution.get("latest_change")
            enriched_rules.append(
                {
                    **rule,
                    "change_attribution": latest_change,
                    "changed_by": latest_change.get("username") if latest_change else None,
                    "changed_at": latest_change.get("event_time") if latest_change else None,
                    "changed_from_ip": latest_change.get("source_ip") if latest_change else None,
                }
            )

        by_severity: dict[str, int] = {}
        for rule in enriched_rules:
            severity = str(rule.get("severity") or "medium")
            by_severity[severity] = by_severity.get(severity, 0) + 1

        return {
            "security_group_count": len(security_groups),
            "internet_exposed_ingress_rules": enriched_rules,
            "permissive_egress_rules": permissive_egress[:20],
            "recent_security_group_changes": sg_changes[:20],
            "attribution_by_security_group": sg_attribution,
            "counts_by_severity": by_severity,
            "healthy": len(enriched_rules) == 0 and len(sg_changes) == 0,
        }

    def _build_network_findings(
        self,
        vpcs: list[dict[str, Any]],
        security_findings: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "vpc_count": len(vpcs),
            "internet_exposed_ingress_count": len(
                security_findings.get("internet_exposed_ingress_rules") or []
            ),
            "internet_exposed_ingress_rules": (
                security_findings.get("internet_exposed_ingress_rules") or []
            )[:30],
            "healthy": len(security_findings.get("internet_exposed_ingress_rules") or []) == 0,
        }

    def _build_finding_summary(
        self,
        ec2_findings: dict[str, Any],
        lambda_findings: dict[str, Any],
        s3_findings: dict[str, Any],
        security_findings: dict[str, Any],
        load_balancer_findings: dict[str, Any],
        auto_scaling_findings: dict[str, Any],
        cloudwatch_findings: dict[str, Any],
        cloudtrail_findings: dict[str, Any],
        incident_attribution: dict[str, Any],
        discovery_assessment: dict[str, Any] | None = None,
        issue_type: str = "full_scan",
        observability: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []

        for item in (observability or {}).get("findings") or []:
            severity = str(item.get("severity") or "medium").lower()
            if severity not in SEVERITY_ORDER:
                severity = "medium"
            findings.append(
                {
                    "severity": severity,
                    "category": "observability",
                    "title": item.get("title") or "Observability finding",
                    "detail": item.get("detail") or "",
                    "resource_id": item.get("source"),
                    "source": item.get("source"),
                    "query": item.get("query"),
                }
            )

        if discovery_assessment:
            for warning in discovery_assessment.get("warnings") or []:
                findings.append(
                    {
                        "severity": "high",
                        "category": "scope",
                        "title": "Investigation scope warning",
                        "detail": warning,
                        "resource_id": None,
                    }
                )
            missing = discovery_assessment.get("referenced_but_not_discovered") or {}
            for instance_id in missing.get("instance_ids") or []:
                findings.append(
                    {
                        "severity": "high",
                        "category": "scope",
                        "title": f"Referenced instance not discovered: {instance_id}",
                        "detail": (
                            f"Instance {instance_id} was referenced in the user query but was not "
                            f"found in region {discovery_assessment.get('region')}."
                        ),
                        "resource_id": instance_id,
                    }
                )
            for tag_key in discovery_assessment.get("referenced_tag_keys") or []:
                matches = discovery_assessment.get("discovered_tags_by_key", {}).get(tag_key) or []
                for match in matches:
                    findings.append(
                        {
                            "severity": "info",
                            "category": "change_audit",
                            "title": f"Tag found on instance: {tag_key}",
                            "detail": (
                                f"Instance {match.get('instance_id')} has tag {tag_key}="
                                f"{match.get('value')}."
                            ),
                            "resource_id": match.get("instance_id"),
                        }
                    )

        for rule in security_findings.get("internet_exposed_ingress_rules") or []:
            detail = (
                f"{rule.get('security_group_id')} ({rule.get('name')}) allows "
                f"{rule.get('protocol')} port {rule.get('port')} from "
                f"{', '.join(rule.get('cidr_blocks') or [])}. Risk: {rule.get('risk')}."
            )
            if rule.get("changed_by"):
                detail += (
                    f" Changed by {rule.get('changed_by')} at {rule.get('changed_at')} "
                    f"from {rule.get('changed_from_ip') or 'unknown IP'}."
                )
            elif rule.get("change_attribution") is None:
                detail += " CloudTrail attribution not found in the lookback window."

            findings.append(
                {
                    "severity": rule.get("severity", "medium"),
                    "category": "security",
                    "title": f"Internet-exposed SG ingress on port {rule.get('port')}",
                    "detail": detail,
                    "resource_id": rule.get("security_group_id"),
                }
            )

        for change in security_findings.get("recent_security_group_changes") or []:
            event_name = change.get("event_name")
            findings.append(
                {
                    "severity": "high"
                    if event_name in {"AuthorizeSecurityGroupIngress", "ModifySecurityGroupRules"}
                    else "medium",
                    "category": "change_audit",
                    "title": f"Security group change: {change.get('event_name')}",
                    "detail": (
                        f"{change.get('username') or change.get('principal_arn')} "
                        f"at {change.get('event_time')} from {change.get('source_ip') or 'unknown IP'}."
                    ),
                    "resource_id": change.get("resource_name"),
                }
            )

        for event in cloudtrail_findings.get("tag_change_events") or []:
            instance_label = ", ".join(event.get("instance_ids") or []) or event.get("resource_name") or "resource"
            tag_detail = event.get("tag_summary") or "tags updated"
            findings.append(
                {
                    "severity": "info",
                    "category": "change_audit",
                    "title": f"Tag change on {instance_label}: {event.get('event_name')}",
                    "detail": (
                        f"{tag_detail} by {event.get('username') or event.get('principal_arn') or 'unknown'} "
                        f"at {event.get('event_time')} from {event.get('source_ip') or 'unknown IP'}."
                    ),
                    "resource_id": (event.get("instance_ids") or [None])[0],
                }
            )

        for instance in ec2_findings.get("problematic_instances") or []:
            findings.append(
                {
                    "severity": "high" if "stopped" in " ".join(instance.get("issues") or []) else "medium",
                    "category": "ec2",
                    "title": f"EC2 issue on {instance.get('instance_id')}",
                    "detail": "; ".join(instance.get("issues") or []),
                    "resource_id": instance.get("instance_id"),
                }
            )

        for incident in incident_attribution.get("stopped_instance_incidents") or []:
            if incident.get("stopped_by"):
                findings.append(
                    {
                        "severity": "high",
                        "category": "ec2",
                        "title": f"Instance stopped by {incident.get('stopped_by')}",
                        "detail": (
                            f"{incident.get('instance_id')} stopped at {incident.get('stopped_at')} "
                            f"from {incident.get('stopped_from_ip') or 'unknown IP'}."
                        ),
                        "resource_id": incident.get("instance_id"),
                    }
                )
            else:
                findings.append(
                    {
                        "severity": "medium",
                        "category": "ec2",
                        "title": f"Stopped instance without CloudTrail stop event: {incident.get('instance_id')}",
                        "detail": (
                            f"{incident.get('instance_id')} is {incident.get('current_state')}. "
                            f"{incident.get('attribution_gap') or 'No stop attribution in lookback window.'}"
                        ),
                        "resource_id": incident.get("instance_id"),
                    }
                )

        for target in load_balancer_findings.get("unhealthy_targets") or []:
            findings.append(
                {
                    "severity": "high",
                    "category": "load_balancer",
                    "title": f"Unhealthy target {target.get('target_id')}",
                    "detail": (
                        f"Target group {target.get('target_group')}: "
                        f"{target.get('health_state')} — {target.get('reason') or target.get('description') or 'unknown'}."
                    ),
                    "resource_id": target.get("target_id"),
                }
            )

        for alarm in cloudwatch_findings.get("alarms_in_alarm_state") or []:
            findings.append(
                {
                    "severity": "high",
                    "category": "performance",
                    "title": f"CloudWatch alarm in ALARM: {alarm.get('alarm_name')}",
                    "detail": (
                        f"Metric {alarm.get('metric_name')} — {alarm.get('state_reason') or 'threshold breached'}."
                    ),
                    "resource_id": alarm.get("alarm_name"),
                }
            )

        for issue in auto_scaling_findings.get("issues") or []:
            findings.append(
                {
                    "severity": "medium",
                    "category": "auto_scaling",
                    "title": f"Auto Scaling issue on {issue.get('auto_scaling_group')}",
                    "detail": issue.get("issue", "scaling issue detected"),
                    "resource_id": issue.get("auto_scaling_group"),
                }
            )

        for function in lambda_findings.get("problematic_functions") or []:
            issues = function.get("issues") or []
            severity = "high" if any(
                any(keyword in str(issue).lower() for keyword in ("timeout", "error", "state"))
                for issue in issues
            ) else "medium"
            findings.append(
                {
                    "severity": severity,
                    "category": "lambda",
                    "title": f"Lambda issue on {function.get('function_name')}",
                    "detail": "; ".join(issues),
                    "resource_id": function.get("function_arn"),
                }
            )

        for bucket in s3_findings.get("problematic_buckets") or []:
            severity = "high" if bucket.get("policy_is_public") is True else "medium"
            findings.append(
                {
                    "severity": severity,
                    "category": "s3",
                    "title": f"S3 security posture issue on {bucket.get('bucket_name')}",
                    "detail": "; ".join(bucket.get("issues") or []),
                    "resource_id": bucket.get("bucket_name"),
                }
            )

        allowed_categories = finding_categories(issue_type)
        if allowed_categories is not None:
            findings = [
                item
                for item in findings
                if str(item.get("category") or "other") in allowed_categories
            ]

        findings.sort(key=lambda item: SEVERITY_ORDER.get(str(item.get("severity")), 99))

        by_category: dict[str, int] = {}
        for item in findings:
            category = str(item.get("category") or "other")
            by_category[category] = by_category.get(category, 0) + 1

        return {
            "total_findings": len(findings),
            "findings": findings[:40],
            "by_category": by_category,
            "by_severity": {
                severity: len([item for item in findings if item.get("severity") == severity])
                for severity in SEVERITY_ORDER
            },
        }

    def _build_load_balancer_findings(
        self,
        load_balancers: list[dict[str, Any]],
        target_groups: list[dict[str, Any]],
    ) -> dict[str, Any]:
        unhealthy_targets: list[dict[str, Any]] = []
        for group in target_groups:
            for target in group.get("targets", []):
                health = str(target.get("health_state") or "").lower()
                if health and health != "healthy":
                    unhealthy_targets.append(
                        {
                            "target_group": group.get("target_group_name"),
                            "target_id": target.get("target_id"),
                            "health_state": target.get("health_state"),
                            "reason": target.get("reason"),
                            "description": target.get("description"),
                        }
                    )

        inactive_lbs = [
            {
                "name": lb.get("name"),
                "state": lb.get("state"),
                "dns_name": lb.get("dns_name"),
            }
            for lb in load_balancers
            if str(lb.get("state") or "").lower() not in {"", "active"}
        ]

        return {
            "load_balancer_count": len(load_balancers),
            "target_group_count": len(target_groups),
            "unhealthy_targets": unhealthy_targets,
            "inactive_load_balancers": inactive_lbs,
            "healthy": not unhealthy_targets and not inactive_lbs,
        }

    def _build_asg_findings(self, groups: list[dict[str, Any]]) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        for group in groups:
            desired = group.get("desired_capacity")
            current = group.get("current_capacity")
            if desired is not None and current is not None and desired != current:
                issues.append(
                    {
                        "auto_scaling_group": group.get("auto_scaling_group_name"),
                        "desired_capacity": desired,
                        "current_capacity": current,
                        "issue": "capacity mismatch",
                    }
                )
            failed_activities = [
                activity
                for activity in group.get("scaling_activities", [])
                if str(activity.get("status_code") or "").lower() not in {"", "successful"}
            ]
            if failed_activities:
                issues.append(
                    {
                        "auto_scaling_group": group.get("auto_scaling_group_name"),
                        "failed_scaling_activities": failed_activities[:5],
                        "issue": "scaling activity failures",
                    }
                )

        return {
            "auto_scaling_group_count": len(groups),
            "issues": issues,
            "healthy": len(issues) == 0,
        }

    def _build_cloudwatch_findings(
        self,
        cloudwatch: dict[str, Any],
        instances: list[dict[str, Any]],
    ) -> dict[str, Any]:
        alarms = cloudwatch.get("alarms") or []
        alarming = [
            {
                "alarm_name": alarm.get("alarm_name"),
                "state_value": alarm.get("state_value"),
                "state_reason": alarm.get("state_reason"),
                "metric_name": alarm.get("metric_name"),
                "threshold": alarm.get("threshold"),
            }
            for alarm in alarms
            if str(alarm.get("state_value") or "").upper() == "ALARM"
        ]
        metrics = cloudwatch.get("metrics") or []
        lambda_metrics = cloudwatch.get("lambda_metrics") or []
        instance_activity = self._summarize_instance_activity(metrics, instances)

        return {
            "collected": cloudwatch.get("collected", False),
            "window": cloudwatch.get("window"),
            "alarms_in_alarm_state": alarming,
            "instance_activity": instance_activity,
            "lambda_invocations": [
                {
                    "function_name": item.get("function_name"),
                    "configured_timeout_sec": item.get("configured_timeout_sec"),
                    "errors": item.get("errors"),
                    "throttles": item.get("throttles"),
                    "max_duration_ms": item.get("max_duration_ms"),
                    "avg_duration_ms": item.get("avg_duration_ms"),
                    "timeout_log_events": item.get("timeout_log_events"),
                    "duration_at_timeout": item.get("duration_at_timeout"),
                }
                for item in lambda_metrics
            ],
            "metric_samples": metrics[: self.MAX_METRICS],
            "error": cloudwatch.get("error"),
            "healthy": len(alarming) == 0
            and all(item.get("activity_status") == "active" for item in instance_activity)
            and all(
                int(item.get("errors") or 0) == 0
                and int(item.get("timeout_log_events") or 0) == 0
                and not item.get("duration_at_timeout")
                for item in lambda_metrics
            ),
        }

    def _summarize_instance_activity(
        self,
        metrics: list[dict[str, Any]],
        instances: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        activity_by_instance: dict[str, dict[str, Any]] = {}

        for metric in metrics:
            if metric.get("metric_name") not in ACTIVITY_METRICS:
                continue
            instance_id = (metric.get("dimensions") or {}).get("InstanceId")
            if not instance_id:
                continue

            datapoints = metric.get("datapoints") or []
            if not datapoints:
                continue

            last_point = datapoints[-1]
            timestamp = last_point.get("timestamp")
            average = last_point.get("average") or 0
            maximum = last_point.get("maximum") or 0
            peak = max(float(average or 0), float(maximum or 0))

            entry = activity_by_instance.setdefault(
                instance_id,
                {
                    "instance_id": instance_id,
                    "last_activity_at": None,
                    "peak_metric": None,
                    "peak_value": 0.0,
                    "datapoint_count": 0,
                },
            )
            entry["datapoint_count"] += len(datapoints)
            if peak >= entry["peak_value"]:
                entry["peak_value"] = peak
                entry["peak_metric"] = metric.get("metric_name")
                entry["last_activity_at"] = timestamp

        summaries: list[dict[str, Any]] = []
        for instance in instances:
            instance_id = instance.get("instance_id")
            if not instance_id:
                continue
            activity = activity_by_instance.get(instance_id)
            state = str(instance.get("state") or "").lower()
            if not activity:
                summaries.append(
                    {
                        "instance_id": instance_id,
                        "name": instance.get("name"),
                        "state": instance.get("state"),
                        "activity_status": "no_metrics_in_window",
                        "interpretation": (
                            "No CloudWatch activity in the selected window. "
                            "Consistent with a stopped instance or no workload."
                            if state in {"stopped", "stopping"}
                            else "No metric datapoints collected in the selected window."
                        ),
                    }
                )
                continue

            summaries.append(
                {
                    "instance_id": instance_id,
                    "name": instance.get("name"),
                    "state": instance.get("state"),
                    "activity_status": "active" if activity["peak_value"] > 0 else "idle",
                    "last_activity_at": activity["last_activity_at"],
                    "peak_metric": activity["peak_metric"],
                    "peak_value": activity["peak_value"],
                    "datapoint_count": activity["datapoint_count"],
                }
            )

        return summaries

    def _build_cloudtrail_findings(
        self,
        cloudtrail: dict[str, Any],
        instances: list[dict[str, Any]],
    ) -> dict[str, Any]:
        events = cloudtrail.get("events") or []
        instance_events = cloudtrail.get("instance_events") or events

        def serialize_event(event: dict[str, Any]) -> dict[str, Any]:
            return {
                "event_time": event.get("event_time"),
                "event_name": event.get("event_name"),
                "username": event.get("username"),
                "principal_arn": event.get("principal_arn"),
                "principal_type": event.get("principal_type"),
                "instance_ids": event.get("instance_ids", []),
                "security_group_ids": event.get("security_group_ids", []),
                "resource_name": event.get("resource_name"),
                "rule_summary": event.get("rule_summary"),
                "tag_summary": event.get("tag_summary"),
                "source_ip": event.get("source_ip"),
                "user_agent": event.get("user_agent"),
                "error_code": event.get("error_code"),
            }

        security_group_events_raw = cloudtrail.get("security_group_events") or [
            event
            for event in events
            if event.get("event_name") in SECURITY_EVENT_NAMES
        ]
        security_group_change_events = [
            serialize_event(event) for event in security_group_events_raw
        ]

        attribution_by_security_group: dict[str, dict[str, Any]] = {}
        for event in security_group_change_events:
            group_ids = event.get("security_group_ids") or []
            resource_name = event.get("resource_name")
            if resource_name and str(resource_name).startswith("sg-"):
                group_ids = list(set([*group_ids, str(resource_name)]))
            for group_id in group_ids:
                entry = attribution_by_security_group.setdefault(
                    group_id,
                    {"security_group_id": group_id, "recent_changes": []},
                )
                entry["recent_changes"].append(event)
                if not entry.get("latest_change"):
                    entry["latest_change"] = event

        state_change_events = [
            serialize_event(event)
            for event in events
            if event.get("event_name") in STATE_CHANGE_EVENT_NAMES
        ]
        instance_state_changes = [
            serialize_event(event)
            for event in instance_events
            if event.get("event_name") in STATE_CHANGE_EVENT_NAMES
        ]

        attribution_by_instance: list[dict[str, Any]] = []
        for instance in instances:
            instance_id = instance.get("instance_id")
            if not instance_id:
                continue
            matching = [
                event
                for event in instance_events
                if instance_id in (event.get("instance_ids") or [])
                or event.get("resource_name") == instance_id
            ]
            stop_events = [
                serialize_event(event)
                for event in matching
                if event.get("event_name") in {"StopInstances", "TerminateInstances", "TerminateInstanceInAutoScalingGroup"}
            ]
            start_events = [
                serialize_event(event)
                for event in matching
                if event.get("event_name") in {"StartInstances", "RunInstances"}
            ]
            tag_events = [
                serialize_event(event)
                for event in matching
                if event.get("event_name") in TAG_EVENT_NAMES
            ]
            if (
                stop_events
                or start_events
                or tag_events
                or str(instance.get("state") or "").lower() in {"stopped", "stopping"}
            ):
                attribution_by_instance.append(
                    {
                        "instance_id": instance_id,
                        "name": instance.get("name"),
                        "state": instance.get("state"),
                        "tags": instance.get("tags") or {},
                        "state_transition_reason": instance.get("state_transition_reason"),
                        "stop_events": stop_events[:5],
                        "start_events": start_events[:3],
                        "tag_events": tag_events[:5],
                        "recent_related_events": [serialize_event(event) for event in matching[:8]],
                    }
                )

        tag_change_events = [
            serialize_event(event)
            for event in events
            if event.get("event_name") in TAG_EVENT_NAMES
        ]

        error_events = [serialize_event(event) for event in events if event.get("error_code")]

        return {
            "collected": cloudtrail.get("collected", False),
            "lookback_hours": cloudtrail.get("lookback_hours"),
            "state_change_events": state_change_events[:30],
            "instance_state_change_events": instance_state_changes[:30],
            "security_group_change_events": security_group_change_events[:30],
            "security_group_events": security_group_change_events[:30],
            "tag_change_events": tag_change_events[:30],
            "attribution_by_security_group": attribution_by_security_group,
            "attribution_by_instance": attribution_by_instance,
            "error_events": error_events[:15],
            "tracked_event_names": cloudtrail.get("tracked_event_names", []),
            "error": cloudtrail.get("error"),
        }

    def _build_incident_attribution(
        self,
        instances: list[dict[str, Any]],
        cloudtrail_findings: dict[str, Any],
        cloudwatch_findings: dict[str, Any],
    ) -> dict[str, Any]:
        activity_map = {
            item["instance_id"]: item
            for item in cloudwatch_findings.get("instance_activity", [])
            if item.get("instance_id")
        }
        attribution_map = {
            item["instance_id"]: item
            for item in cloudtrail_findings.get("attribution_by_instance", [])
            if item.get("instance_id")
        }

        incidents: list[dict[str, Any]] = []
        for instance in instances:
            instance_id = instance.get("instance_id")
            state = str(instance.get("state") or "").lower()
            if state not in {"stopped", "stopping", "terminated", "shutting-down"}:
                continue

            attribution = attribution_map.get(instance_id, {})
            activity = activity_map.get(instance_id, {})
            stop_events = attribution.get("stop_events") or []
            latest_stop = stop_events[0] if stop_events else None

            incident: dict[str, Any] = {
                "instance_id": instance_id,
                "name": instance.get("name"),
                "current_state": instance.get("state"),
                "state_transition_reason": instance.get("state_transition_reason"),
                "cloudtrail_stop_event_found": bool(latest_stop),
                "cloudwatch_last_activity_at": activity.get("last_activity_at"),
                "cloudwatch_activity_status": activity.get("activity_status"),
            }

            if latest_stop:
                incident.update(
                    {
                        "stopped_by": latest_stop.get("username") or latest_stop.get("principal_arn"),
                        "stopped_at": latest_stop.get("event_time"),
                        "stopped_from_ip": latest_stop.get("source_ip"),
                        "stop_event_name": latest_stop.get("event_name"),
                        "principal_arn": latest_stop.get("principal_arn"),
                    }
                )
            else:
                incident["attribution_gap"] = (
                    "No StopInstances/TerminateInstances CloudTrail event found in the lookback window. "
                    "The instance may have been stopped before the window, by a service not logged here, "
                    "or CloudTrail may not be enabled for this region/account."
                )

            incidents.append(incident)

        return {
            "stopped_instance_incidents": incidents,
            "analysis_note": (
                "Use this section when troubleshooting EC2 availability or full_scan."
                if incidents
                else "No stopped-instance incidents detected."
            ),
        }

    def _build_config_findings(self, aws_config: dict[str, Any]) -> dict[str, Any]:
        changes = aws_config.get("recent_changes") or []
        return {
            "enabled": aws_config.get("enabled", False),
            "recorder_name": aws_config.get("recorder_name"),
            "recent_changes": changes[:20],
            "error": aws_config.get("error"),
        }

    def _summarize_topology_kinds(self, graph_nodes: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for node in graph_nodes:
            kind = str(node.get("kind") or "other")
            counts[kind] = counts.get(kind, 0) + 1
        return counts
