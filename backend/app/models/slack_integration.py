"""Slack integration request/response models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


SlackDeliveryMethod = Literal["webhook", "channel"]


class SlackIntegrationSettings(BaseModel):
    enabled: bool = False
    delivery_method: SlackDeliveryMethod = "webhook"
    channel: str = ""
    webhook_url: str | None = Field(
        default=None,
        description="Set to update webhook URL; omit or null to keep existing value.",
    )
    notify_kubernetes: bool = True
    notify_aws: bool = True
    notify_cloud_cost: bool = True
    notify_pr_reviewer: bool = True
    notify_performance: bool = True
    notify_security: bool = True


class SlackIntegrationResponse(BaseModel):
    enabled: bool
    delivery_method: SlackDeliveryMethod
    channel: str
    webhook_url_configured: bool
    webhook_url_preview: str | None = None
    notify_kubernetes: bool
    notify_aws: bool
    notify_cloud_cost: bool
    notify_pr_reviewer: bool
    notify_performance: bool
    notify_security: bool
    instance_bot_configured: bool
    instance_webhook_configured: bool


class SlackTestResponse(BaseModel):
    status: str
    message: str
