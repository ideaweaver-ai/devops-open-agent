"""Map AWS issue types to discovery and AI finding scope."""

from __future__ import annotations

FULL_DISCOVERY = frozenset(
    {"ec2", "lambda", "s3", "network", "security_groups", "load_balancers"}
)

FOCUSED_DISCOVERY: dict[str, frozenset[str]] = {
    "lambda": frozenset({"lambda"}),
    "s3": frozenset({"s3"}),
    "ec2_availability": frozenset({"ec2", "network", "security_groups"}),
    "network": frozenset({"network", "security_groups", "ec2"}),
    "security": frozenset({"network", "security_groups", "ec2"}),
    "load_balancer": frozenset({"ec2", "load_balancers", "network"}),
    "performance": frozenset({"ec2", "lambda"}),
    "change_audit": frozenset({"ec2", "network", "security_groups"}),
}

FOCUSED_FINDING_CATEGORIES: dict[str, frozenset[str]] = {
    "lambda": frozenset({"lambda", "observability"}),
    "s3": frozenset({"s3", "observability"}),
    "ec2_availability": frozenset({"ec2", "change_audit", "scope", "observability"}),
    "network": frozenset({"security", "scope", "observability"}),
    "security": frozenset({"security", "change_audit", "scope", "observability"}),
    "load_balancer": frozenset({"load_balancer", "ec2", "scope", "observability"}),
    "performance": frozenset({"performance", "ec2", "lambda", "scope", "observability"}),
    "change_audit": frozenset({"change_audit", "scope", "observability"}),
}


def discovery_scope(issue_type: str) -> frozenset[str]:
    if issue_type == "full_scan":
        return FULL_DISCOVERY
    return FOCUSED_DISCOVERY.get(issue_type, FULL_DISCOVERY)


def finding_categories(issue_type: str) -> frozenset[str] | None:
    if issue_type == "full_scan":
        return None
    return FOCUSED_FINDING_CATEGORIES.get(issue_type)
