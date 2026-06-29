"""PagerDuty notification cooldown to reduce alert fatigue."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import PagerDutyNotificationCooldown, UserPagerDutyIntegration


def cooldown_scope_key(user_id: UUID | None) -> str:
    if user_id is not None:
        return f"user:{user_id}"
    return "instance"


class PagerDutyCooldownService:
    """Enforce minimum interval between PagerDuty notifications."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def _cooldown_minutes(
        self,
        session: AsyncSession,
        user_id: UUID | None,
    ) -> int:
        if user_id is not None:
            result = await session.execute(
                select(UserPagerDutyIntegration).where(
                    UserPagerDutyIntegration.user_id == user_id
                )
            )
            row = result.scalar_one_or_none()
            if row is not None:
                return max(0, row.notification_cooldown_minutes)
        return max(0, self.settings.pagerduty_notification_cooldown_minutes)

    async def seconds_until_send_allowed(
        self,
        session: AsyncSession,
        user_id: UUID | None,
    ) -> int:
        minutes = await self._cooldown_minutes(session, user_id)
        if minutes <= 0:
            return 0

        cooldown = timedelta(minutes=minutes)
        row = await self._get_row(session, user_id)
        if row is None:
            return 0

        elapsed = datetime.now(timezone.utc) - row.last_sent_at
        remaining = cooldown - elapsed
        if remaining.total_seconds() <= 0:
            return 0
        return int(remaining.total_seconds())

    async def mark_sent(
        self,
        session: AsyncSession,
        user_id: UUID | None,
    ) -> None:
        scope_key = cooldown_scope_key(user_id)
        now = datetime.now(timezone.utc)
        row = await self._get_row(session, user_id)
        if row is None:
            session.add(PagerDutyNotificationCooldown(scope_key=scope_key, last_sent_at=now))
        else:
            row.last_sent_at = now
        await session.commit()

    async def _get_row(
        self,
        session: AsyncSession,
        user_id: UUID | None,
    ) -> PagerDutyNotificationCooldown | None:
        scope_key = cooldown_scope_key(user_id)
        result = await session.execute(
            select(PagerDutyNotificationCooldown).where(
                PagerDutyNotificationCooldown.scope_key == scope_key
            )
        )
        return result.scalar_one_or_none()
