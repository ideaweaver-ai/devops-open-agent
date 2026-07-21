"""Prometheus integration request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PrometheusIntegrationSettings(BaseModel):
    enabled: bool = False
    url: str = Field(
        default="",
        description="Prometheus endpoint, e.g. http://prometheus:9090",
    )
    bearer_token: str | None = Field(
        default=None,
        description="Set to update the bearer token; omit or null to keep existing value.",
    )
    basic_auth_user: str | None = Field(
        default=None,
        description="Optional basic-auth username.",
    )
    basic_auth_password: str | None = Field(
        default=None,
        description="Set to update the basic-auth password; omit or null to keep existing.",
    )
    use_kubernetes: bool = True


class PrometheusIntegrationResponse(BaseModel):
    enabled: bool
    url: str
    bearer_token_configured: bool
    bearer_token_preview: str | None = None
    basic_auth_user: str
    basic_auth_password_configured: bool
    use_kubernetes: bool
    instance_url_configured: bool


class PrometheusTestResponse(BaseModel):
    status: str
    message: str
    version: str | None = None
