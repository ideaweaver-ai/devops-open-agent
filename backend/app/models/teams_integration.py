"""Microsoft Teams integration request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TeamsIntegrationSettings(BaseModel):
    enabled: bool = False
    webhook_url: str | None = Field(
        default=None,
        description="Set to update webhook URL; omit or null to keep existing value.",
    )
    notify_kubernetes: bool = True
    notify_aws: bool = True
    notify_cloud_cost: bool = True
    notify_pr_reviewer: bool = True


class TeamsIntegrationResponse(BaseModel):
    enabled: bool
    webhook_url_configured: bool
    webhook_url_preview: str | None = None
    notify_kubernetes: bool
    notify_aws: bool
    notify_cloud_cost: bool
    notify_pr_reviewer: bool
    instance_webhook_configured: bool


class TeamsTestResponse(BaseModel):
    status: str
    message: str
