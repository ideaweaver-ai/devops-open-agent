"""Persist and load per-user Grafana integration settings."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import UserGrafanaIntegration
from app.models.grafana_integration import (
    GrafanaIntegrationResponse,
    GrafanaIntegrationSettings,
)
from app.services.mcp_settings_service import mask_api_key


@dataclass(frozen=True)
class GrafanaConnection:
    url: str
    api_token: str | None = None


class GrafanaSettingsService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def get_settings(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> GrafanaIntegrationResponse:
        row = await self._get_row(session, user_id)
        token = row.api_token if row else None
        return GrafanaIntegrationResponse(
            enabled=bool(row.enabled) if row else False,
            url=(row.url or "") if row else "",
            api_token_configured=bool(token),
            api_token_preview=mask_api_key(token),
            use_kubernetes=row.use_kubernetes if row else True,
            instance_url_configured=bool(self.settings.grafana_instance_url.strip()),
        )

    async def upsert_settings(
        self,
        session: AsyncSession,
        user_id: UUID,
        payload: GrafanaIntegrationSettings,
    ) -> GrafanaIntegrationResponse:
        row = await self._get_row(session, user_id)
        if row is None:
            row = UserGrafanaIntegration(user_id=user_id)
            session.add(row)

        row.enabled = payload.enabled
        row.url = payload.url.strip()
        row.use_kubernetes = payload.use_kubernetes
        if payload.api_token is not None and payload.api_token.strip():
            row.api_token = payload.api_token.strip()

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
    ) -> GrafanaConnection | None:
        if user_id is not None:
            row = await self._get_row(session, user_id)
            if row and (row.enabled or not require_enabled):
                if not (require_kubernetes and require_enabled and not row.use_kubernetes):
                    url = (row.url or "").strip()
                    if url:
                        return GrafanaConnection(
                            url=url.rstrip("/"),
                            api_token=(row.api_token or "").strip() or None,
                        )

        instance_url = self.settings.grafana_instance_url.strip()
        if instance_url:
            return GrafanaConnection(
                url=instance_url.rstrip("/"),
                api_token=self.settings.grafana_instance_api_token.strip() or None,
            )
        return None

    @staticmethod
    async def _get_row(
        session: AsyncSession,
        user_id: UUID,
    ) -> UserGrafanaIntegration | None:
        result = await session.execute(
            select(UserGrafanaIntegration).where(UserGrafanaIntegration.user_id == user_id)
        )
        return result.scalar_one_or_none()
