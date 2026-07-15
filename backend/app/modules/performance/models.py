"""Pydantic models for Performance Debugging."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


MAX_HOSTS = 50

HostStatus = Literal[
    "pending",
    "collecting",
    "analyzing",
    "completed",
    "failed",
]

JobStatus = Literal["queued", "running", "completed", "failed"]


def normalize_hosts(raw_hosts: list[str]) -> list[str]:
    """Strip blanks/comments, dedupe (preserve order), and enforce max size."""
    seen: set[str] = set()
    hosts: list[str] = []
    for item in raw_hosts:
        line = (item or "").strip()
        if not line or line.startswith("#"):
            continue
        # Allow user@host; reject whitespace / shell metacharacters
        if any(ch.isspace() for ch in line) or any(ch in line for ch in ";|&`$()<>"):
            continue
        if line in seen:
            continue
        seen.add(line)
        hosts.append(line)
        if len(hosts) >= MAX_HOSTS:
            break
    return hosts


class PerformanceDebugRequest(BaseModel):
    hosts: list[str] = Field(
        ...,
        min_length=1,
        description="Hostnames or user@host targets (passwordless SSH required)",
    )

    @field_validator("hosts", mode="before")
    @classmethod
    def _coerce_hosts(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            value = value.splitlines()
        if not isinstance(value, list):
            raise ValueError("hosts must be a list of strings")
        hosts = normalize_hosts([str(item) for item in value])
        if not hosts:
            raise ValueError("At least one valid hostname is required")
        return hosts


class PerformanceDebugStartResponse(BaseModel):
    debug_id: str
    status: JobStatus = "queued"
    message: str = "Performance debugging started"
    host_count: int = 0


class HostDebugResult(BaseModel):
    host: str
    status: HostStatus = "pending"
    message: str | None = None
    evidence: str | None = None
    analysis: str | None = None
    summary: str | None = None
    severity: str | None = None
    error: str | None = None


class PerformanceDebugStatusResponse(BaseModel):
    debug_id: str
    status: JobStatus
    current_step: str | None = None
    progress_percentage: int = 0
    hosts: list[HostDebugResult] = Field(default_factory=list)
    error: str | None = None


class PerformanceDebugDetailResponse(PerformanceDebugStatusResponse):
    agent_type: str = "performance"
    created_at: str | None = None
    updated_at: str | None = None
    overall_summary: str | None = None


class PerformanceDebugHistoryItem(BaseModel):
    debug_id: str
    status: JobStatus
    host_count: int = 0
    hosts_summary: str = ""
    overall_summary: str | None = None
    created_at: str | None = None


class PerformanceDebugHistoryResponse(BaseModel):
    jobs: list[PerformanceDebugHistoryItem] = Field(default_factory=list)
