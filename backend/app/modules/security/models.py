"""Pydantic models for Security Scanning."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ScanType(str, Enum):
    IMAGE = "image"
    KUBERNETES = "kubernetes"


ScanJobStatus = Literal["queued", "running", "completed", "failed"]

ALL_SEVERITIES = ["UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


class SecurityScanRequest(BaseModel):
    scan_type: ScanType
    image_name: str | None = Field(
        default=None,
        description="Container image to scan (required for image scans)",
    )
    namespace: str | None = Field(
        default=None,
        description="K8s namespace to scope the scan (None = all namespaces)",
    )
    context: str | None = Field(
        default=None,
        description="Kubeconfig context / cluster to scan (uses active context when empty)",
    )
    include_ai: bool = Field(
        default=True,
        description="Run LLM analysis on scan findings",
    )
    severity_filter: list[str] = Field(
        default_factory=lambda: list(ALL_SEVERITIES),
        description="Severity levels to include",
    )


class VulnerabilityFinding(BaseModel):
    vulnerability_id: str
    pkg_name: str
    installed_version: str
    fixed_version: str | None = None
    severity: str
    title: str
    description: str


class MisconfigFinding(BaseModel):
    id: str
    title: str
    description: str
    severity: str
    resolution: str
    resource: str | None = None


class ScanResult(BaseModel):
    scan_type: ScanType
    target: str
    vulnerabilities: list[VulnerabilityFinding] = Field(default_factory=list)
    misconfigurations: list[MisconfigFinding] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    ai_analysis: str | None = None
    llm_provider: str | None = None
    llm_error: str | None = None


class SecurityScanStartResponse(BaseModel):
    scan_id: str
    status: ScanJobStatus = "queued"
    message: str = "Security scan started"


class SecurityScanStatusResponse(BaseModel):
    scan_id: str
    status: ScanJobStatus
    current_step: str | None = None
    progress_percentage: int = 0
    error: str | None = None


class SecurityScanDetailResponse(SecurityScanStatusResponse):
    agent_type: str = "security"
    created_at: str | None = None
    updated_at: str | None = None
    result: ScanResult | None = None
