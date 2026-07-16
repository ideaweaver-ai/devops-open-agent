"""PagerDuty integration request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PagerDutyIntegrationSettings(BaseModel):
    enabled: bool = False
    routing_key: str | None = Field(
        default=None,
        description="Set to update routing key; omit or null to keep existing value.",
    )
    notification_cooldown_minutes: int = Field(
        default=60,
        ge=0,
        le=1440,
        description="Minimum minutes between PagerDuty alerts for this user (0 = no cooldown).",
    )
    notify_kubernetes: bool = True
    notify_aws: bool = True
    notify_cloud_cost: bool = True
    notify_pr_reviewer: bool = True
    notify_performance: bool = True
    notify_security: bool = True


class PagerDutyIntegrationResponse(BaseModel):
    enabled: bool
    routing_key_configured: bool
    routing_key_preview: str | None = None
    notification_cooldown_minutes: int
    default_cooldown_minutes: int
    notify_kubernetes: bool
    notify_aws: bool
    notify_cloud_cost: bool
    notify_pr_reviewer: bool
    notify_performance: bool
    notify_security: bool
    instance_routing_key_configured: bool


class PagerDutyTestResponse(BaseModel):
    status: str
    message: str
