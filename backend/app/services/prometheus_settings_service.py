"""Persist and load per-user Prometheus integration settings."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import UserPrometheusIntegration
from app.models.prometheus_integration import (
    PrometheusIntegrationResponse,
    PrometheusIntegrationSettings,
)
from app.services.mcp_settings_service import mask_api_key


@dataclass(frozen=True)
class PrometheusConnection:
    url: str
    bearer_token: str | None = None
    basic_auth_user: str | None = None
    basic_auth_password: str | None = None


class PrometheusSettingsService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def get_settings(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> PrometheusIntegrationResponse:
        row = await self._get_row(session, user_id)
        token = row.bearer_token if row else None
        password = row.basic_auth_password if row else None
        return PrometheusIntegrationResponse(
            enabled=bool(row.enabled) if row else False,
            url=(row.url or "") if row else "",
            bearer_token_configured=bool(token),
            bearer_token_preview=mask_api_key(token),
            basic_auth_user=(row.basic_auth_user or "") if row else "",
            basic_auth_password_configured=bool(password),
            use_kubernetes=row.use_kubernetes if row else True,
            instance_url_configured=bool(self.settings.prometheus_instance_url.strip()),
        )

    async def upsert_settings(
        self,
        session: AsyncSession,
        user_id: UUID,
        payload: PrometheusIntegrationSettings,
    ) -> PrometheusIntegrationResponse:
        row = await self._get_row(session, user_id)
        if row is None:
            row = UserPrometheusIntegration(user_id=user_id)
            session.add(row)

        row.enabled = payload.enabled
        row.url = payload.url.strip()
        row.use_kubernetes = payload.use_kubernetes
        if payload.basic_auth_user is not None:
            row.basic_auth_user = payload.basic_auth_user.strip() or None
        if payload.bearer_token is not None and payload.bearer_token.strip():
            row.bearer_token = payload.bearer_token.strip()
        if payload.basic_auth_password is not None and payload.basic_auth_password.strip():
            row.basic_auth_password = payload.basic_auth_password.strip()

        await session.commit()
        await session.refresh(row)
        return await self.get_settings(session, user_id)

    async def resolve_connection(
        self,
        session: AsyncSession,
        user_id: UUID | None,
        *,
        require_enabled: bool = True,
        require_kubernetes: bool = True,
    ) -> PrometheusConnection | None:
        if user_id is not None:
            row = await self._get_row(session, user_id)
            if row and (row.enabled or not require_enabled):
                if require_kubernetes and require_enabled and not row.use_kubernetes:
                    return None
                url = (row.url or "").strip()
                if url:
                    return PrometheusConnection(
                        url=url.rstrip("/"),
                        bearer_token=(row.bearer_token or "").strip() or None,
                        basic_auth_user=(row.basic_auth_user or "").strip() or None,
                        basic_auth_password=(row.basic_auth_password or "").strip() or None,
                    )

        instance_url = self.settings.prometheus_instance_url.strip()
        if instance_url:
            return PrometheusConnection(
                url=instance_url.rstrip("/"),
                bearer_token=self.settings.prometheus_instance_bearer_token.strip() or None,
                basic_auth_user=self.settings.prometheus_instance_basic_auth_user.strip() or None,
                basic_auth_password=self.settings.prometheus_instance_basic_auth_password.strip()
                or None,
            )
        return None

    @staticmethod
    async def _get_row(
        session: AsyncSession,
        user_id: UUID,
    ) -> UserPrometheusIntegration | None:
        result = await session.execute(
            select(UserPrometheusIntegration).where(
                UserPrometheusIntegration.user_id == user_id
            )
        )
        return result.scalar_one_or_none()
