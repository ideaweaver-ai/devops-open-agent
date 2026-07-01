"""Microsoft Teams notification cooldown to reduce alert fatigue."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import TeamsNotificationCooldown
from app.services.slack_cooldown_service import cooldown_scope_key


class TeamsCooldownService:
    """Enforce minimum interval between Teams notifications."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def cooldown(self) -> timedelta:
        minutes = max(0, self.settings.teams_notification_cooldown_minutes)
        return timedelta(minutes=minutes)

    async def seconds_until_send_allowed(
        self,
        session: AsyncSession,
        user_id: UUID | None,
    ) -> int:
        if self.cooldown.total_seconds() <= 0:
            return 0

        row = await self._get_row(session, user_id)
        if row is None:
            return 0

        elapsed = datetime.now(timezone.utc) - row.last_sent_at
        remaining = self.cooldown - elapsed
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
            session.add(TeamsNotificationCooldown(scope_key=scope_key, last_sent_at=now))
        else:
            row.last_sent_at = now
        await session.commit()

    async def _get_row(
        self,
        session: AsyncSession,
        user_id: UUID | None,
    ) -> TeamsNotificationCooldown | None:
        scope_key = cooldown_scope_key(user_id)
        result = await session.execute(
            select(TeamsNotificationCooldown).where(
                TeamsNotificationCooldown.scope_key == scope_key
            )
        )
        return result.scalar_one_or_none()
