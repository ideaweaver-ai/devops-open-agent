"""Persist and load per-user Qdrant (RAG) integration settings."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import UserQdrantIntegration
from app.integrations.qdrant.embeddings import (
    resolve_embedding_model,
    resolve_embedding_provider,
)
from app.models.qdrant_integration import (
    QdrantIntegrationResponse,
    QdrantIntegrationSettings,
)
from app.services.mcp_settings_service import mask_api_key


@dataclass(frozen=True)
class QdrantConnection:
    url: str
    api_key: str | None
    collection: str


class QdrantSettingsService:
    """CRUD for user Qdrant vector database preferences."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _default_collection(self) -> str:
        return self.settings.qdrant_collection.strip() or "devops_open_agent_investigations"

    async def get_settings(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> QdrantIntegrationResponse:
        row = await self._get_row(session, user_id)
        api_key = row.api_key if row else None
        provider = resolve_embedding_provider(self.settings)
        return QdrantIntegrationResponse(
            enabled=bool(row.enabled) if row else False,
            url=(row.url or "") if row else "",
            api_key_configured=bool(api_key),
            api_key_preview=mask_api_key(api_key),
            collection=(row.collection or "").strip() if row and row.collection else self._default_collection(),
            use_kubernetes=row.use_kubernetes if row else True,
            use_aws=row.use_aws if row else True,
            use_cloud_cost=row.use_cloud_cost if row else True,
            use_performance=row.use_performance if row else True,
            use_security=row.use_security if row else True,
            instance_url_configured=bool(self.settings.qdrant_instance_url.strip()),
            embedding_provider=provider,
            embedding_model=resolve_embedding_model(self.settings, provider),
        )

    async def upsert_settings(
        self,
        session: AsyncSession,
        user_id: UUID,
        payload: QdrantIntegrationSettings,
    ) -> QdrantIntegrationResponse:
        row = await self._get_row(session, user_id)
        if row is None:
            row = UserQdrantIntegration(user_id=user_id)
            session.add(row)

        row.enabled = payload.enabled
        row.url = payload.url.strip()
        row.use_kubernetes = payload.use_kubernetes
        row.use_aws = payload.use_aws
        row.use_cloud_cost = payload.use_cloud_cost
        row.use_performance = payload.use_performance
        row.use_security = payload.use_security

        if payload.collection is not None:
            row.collection = payload.collection.strip() or None
        if payload.api_key is not None and payload.api_key.strip():
            row.api_key = payload.api_key.strip()

        await session.commit()
        await session.refresh(row)
        return await self.get_settings(session, user_id)

    async def resolve_connection(
        self,
        session: AsyncSession,
        user_id: UUID | None,
        agent_type: str,
        *,
        require_enabled: bool = True,
    ) -> QdrantConnection | None:
        """Return Qdrant connection when RAG should be used for this agent."""
        if user_id is not None:
            row = await self._get_row(session, user_id)
            if row and (row.enabled or not require_enabled):
                if not require_enabled or self._agent_enabled(row, agent_type):
                    url = (row.url or "").strip()
                    if url:
                        return QdrantConnection(
                            url=url,
                            api_key=(row.api_key or "").strip() or None,
                            collection=(row.collection or "").strip() or self._default_collection(),
                        )

        instance_url = self.settings.qdrant_instance_url.strip()
        if instance_url:
            return QdrantConnection(
                url=instance_url,
                api_key=self.settings.qdrant_instance_api_key.strip() or None,
                collection=self._default_collection(),
            )

        return None

    @staticmethod
    def _agent_enabled(row: UserQdrantIntegration, agent_type: str) -> bool:
        normalized = agent_type.replace("-", "_")
        if normalized == "kubernetes":
            return row.use_kubernetes
        if normalized == "aws":
            return row.use_aws
        if normalized == "cloud_cost":
            return row.use_cloud_cost
        if normalized == "performance":
            return row.use_performance
        if normalized == "security":
            return row.use_security
        return True

    @staticmethod
    async def _get_row(
        session: AsyncSession,
        user_id: UUID,
    ) -> UserQdrantIntegration | None:
        result = await session.execute(
            select(UserQdrantIntegration).where(UserQdrantIntegration.user_id == user_id)
        )
        return result.scalar_one_or_none()
