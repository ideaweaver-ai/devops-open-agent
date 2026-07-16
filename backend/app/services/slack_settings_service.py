"""Persist and load per-user Slack integration settings."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import UserSlackIntegration
from app.models.slack_integration import SlackIntegrationResponse, SlackIntegrationSettings


def mask_webhook_url(webhook_url: str | None) -> str | None:
    if not webhook_url:
        return None
    trimmed = webhook_url.strip()
    if len(trimmed) <= 12:
        return "..." + trimmed[-4:]
    return "..." + trimmed[-8:]


class SlackSettingsService:
    """CRUD for user Slack notification preferences."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def get_settings(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> SlackIntegrationResponse:
        row = await self._get_row(session, user_id)
        webhook_url = row.webhook_url if row else None
        return SlackIntegrationResponse(
            enabled=bool(row.enabled) if row else False,
            delivery_method=(row.delivery_method if row else "webhook"),  # type: ignore[arg-type]
            channel=(row.channel or "") if row else "",
            webhook_url_configured=bool(webhook_url),
            webhook_url_preview=mask_webhook_url(webhook_url),
            notify_kubernetes=row.notify_kubernetes if row else True,
            notify_aws=row.notify_aws if row else True,
            notify_cloud_cost=row.notify_cloud_cost if row else True,
            notify_pr_reviewer=row.notify_pr_reviewer if row else True,
            notify_performance=row.notify_performance if row else True,
            notify_security=row.notify_security if row else True,
            instance_bot_configured=bool(self.settings.slack_bot_token.strip()),
            instance_webhook_configured=bool(self.settings.slack_instance_webhook_url.strip()),
        )

    async def upsert_settings(
        self,
        session: AsyncSession,
        user_id: UUID,
        payload: SlackIntegrationSettings,
    ) -> SlackIntegrationResponse:
        row = await self._get_row(session, user_id)
        if row is None:
            row = UserSlackIntegration(user_id=user_id)
            session.add(row)

        row.enabled = payload.enabled
        row.delivery_method = payload.delivery_method
        row.channel = payload.channel.strip() or None
        row.notify_kubernetes = payload.notify_kubernetes
        row.notify_aws = payload.notify_aws
        row.notify_cloud_cost = payload.notify_cloud_cost
        row.notify_pr_reviewer = payload.notify_pr_reviewer
        row.notify_performance = payload.notify_performance
        row.notify_security = payload.notify_security

        if payload.webhook_url is not None and payload.webhook_url.strip():
            row.webhook_url = payload.webhook_url.strip()

        await session.commit()
        await session.refresh(row)
        return await self.get_settings(session, user_id)

    async def resolve_delivery(
        self,
        session: AsyncSession,
        user_id: UUID | None,
        agent_type: str,
        *,
        require_enabled: bool = True,
    ) -> tuple[str | None, str | None]:
        """Return (webhook_url, channel) for delivery, or (None, None) if disabled."""
        if user_id is not None:
            row = await self._get_row(session, user_id)
            if row and (row.enabled or not require_enabled):
                if not require_enabled or self._agent_enabled(row, agent_type):
                    webhook, channel = self._row_delivery(row)
                    if webhook or channel:
                        return webhook, channel

        if self.settings.slack_instance_webhook_url.strip():
            return self.settings.slack_instance_webhook_url.strip(), None

        return None, None

    def _row_delivery(self, row: UserSlackIntegration) -> tuple[str | None, str | None]:
        if row.delivery_method == "channel":
            channel = (row.channel or "").strip()
            if channel and self.settings.slack_bot_token.strip():
                return None, channel
            return None, None

        webhook = (row.webhook_url or "").strip()
        if webhook:
            return webhook, None
        return None, None

    @staticmethod
    def _agent_enabled(row: UserSlackIntegration, agent_type: str) -> bool:
        normalized = agent_type.replace("-", "_")
        if normalized == "kubernetes":
            return row.notify_kubernetes
        if normalized == "aws":
            return row.notify_aws
        if normalized == "cloud_cost":
            return row.notify_cloud_cost
        if normalized in {"pr_reviewer", "pr-reviewer"}:
            return row.notify_pr_reviewer
        if normalized == "performance":
            return row.notify_performance
        if normalized == "security":
            return row.notify_security
        return True

    @staticmethod
    async def _get_row(
        session: AsyncSession,
        user_id: UUID,
    ) -> UserSlackIntegration | None:
        result = await session.execute(
            select(UserSlackIntegration).where(UserSlackIntegration.user_id == user_id)
        )
        return result.scalar_one_or_none()
