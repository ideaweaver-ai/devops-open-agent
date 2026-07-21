"""Grafana integration request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GrafanaIntegrationSettings(BaseModel):
    enabled: bool = False
    url: str = Field(
        default="",
        description="Grafana endpoint, e.g. http://grafana:3000",
    )
    api_token: str | None = Field(
        default=None,
        description="Set to update the Grafana API token; omit or null to keep existing value.",
    )
    use_kubernetes: bool = True


class GrafanaIntegrationResponse(BaseModel):
    enabled: bool
    url: str
    api_token_configured: bool
    api_token_preview: str | None = None
    use_kubernetes: bool
    instance_url_configured: bool


class GrafanaTestResponse(BaseModel):
    status: str
    message: str
    version: str | None = None
    org_name: str | None = None
