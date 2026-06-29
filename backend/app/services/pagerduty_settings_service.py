"""Persist and load per-user PagerDuty integration settings."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import UserPagerDutyIntegration
from app.models.pagerduty_integration import (
    PagerDutyIntegrationResponse,
    PagerDutyIntegrationSettings,
)


def mask_routing_key(routing_key: str | None) -> str | None:
    if not routing_key:
        return None
    trimmed = routing_key.strip()
    if len(trimmed) <= 8:
        return "..." + trimmed[-4:]
    return "..." + trimmed[-8:]


class PagerDutySettingsService:
    """CRUD for user PagerDuty notification preferences."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def get_settings(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> PagerDutyIntegrationResponse:
        row = await self._get_row(session, user_id)
        routing_key = row.routing_key if row else None
        return PagerDutyIntegrationResponse(
            enabled=bool(row.enabled) if row else False,
            routing_key_configured=bool(routing_key),
            routing_key_preview=mask_routing_key(routing_key),
            notification_cooldown_minutes=(
                row.notification_cooldown_minutes if row else 60
            ),
            default_cooldown_minutes=max(
                0, self.settings.pagerduty_notification_cooldown_minutes
            ),
            notify_kubernetes=row.notify_kubernetes if row else True,
            notify_aws=row.notify_aws if row else True,
            notify_cloud_cost=row.notify_cloud_cost if row else True,
            notify_pr_reviewer=row.notify_pr_reviewer if row else True,
            instance_routing_key_configured=bool(
                self.settings.pagerduty_instance_routing_key.strip()
            ),
        )

    async def upsert_settings(
        self,
        session: AsyncSession,
        user_id: UUID,
        payload: PagerDutyIntegrationSettings,
    ) -> PagerDutyIntegrationResponse:
        row = await self._get_row(session, user_id)
        if row is None:
            row = UserPagerDutyIntegration(user_id=user_id)
            session.add(row)

        row.enabled = payload.enabled
        row.notification_cooldown_minutes = max(0, min(1440, payload.notification_cooldown_minutes))
        row.notify_kubernetes = payload.notify_kubernetes
        row.notify_aws = payload.notify_aws
        row.notify_cloud_cost = payload.notify_cloud_cost
        row.notify_pr_reviewer = payload.notify_pr_reviewer

        if payload.routing_key is not None and payload.routing_key.strip():
            row.routing_key = payload.routing_key.strip()

        await session.commit()
        await session.refresh(row)
        return await self.get_settings(session, user_id)

    async def resolve_routing_key(
        self,
        session: AsyncSession,
        user_id: UUID | None,
        agent_type: str,
        *,
        require_enabled: bool = True,
    ) -> str | None:
        """Return routing key for delivery, or None if disabled."""
        if user_id is not None:
            row = await self._get_row(session, user_id)
            if row and (row.enabled or not require_enabled):
                if not require_enabled or self._agent_enabled(row, agent_type):
                    key = (row.routing_key or "").strip()
                    if key:
                        return key

        instance_key = self.settings.pagerduty_instance_routing_key.strip()
        if instance_key:
            return instance_key

        return None

    @staticmethod
    def _agent_enabled(row: UserPagerDutyIntegration, agent_type: str) -> bool:
        normalized = agent_type.replace("-", "_")
        if normalized == "kubernetes":
            return row.notify_kubernetes
        if normalized == "aws":
            return row.notify_aws
        if normalized == "cloud_cost":
            return row.notify_cloud_cost
        if normalized in {"pr_reviewer", "pr-reviewer"}:
            return row.notify_pr_reviewer
        return True

    @staticmethod
    async def _get_row(
        session: AsyncSession,
        user_id: UUID,
    ) -> UserPagerDutyIntegration | None:
        result = await session.execute(
            select(UserPagerDutyIntegration).where(
                UserPagerDutyIntegration.user_id == user_id
            )
        )
        return result.scalar_one_or_none()
