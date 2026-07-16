"""Persist and load per-user MCP integration settings."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import UserMcpIntegration
from app.integrations.mcp.url_policy import McpUrlPolicyError, validate_mcp_url
from app.integrations.mcp.official_servers import list_official_mcp_servers
from app.models.mcp_integration import McpIntegrationResponse, McpIntegrationSettings
from app.services.mcp_access_service import McpAccessService


def mask_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    trimmed = api_key.strip()
    if len(trimmed) <= 8:
        return "..." + trimmed[-4:]
    return "..." + trimmed[-8:]


class McpSettingsService:
    """CRUD for user MCP server preferences."""

    def __init__(
        self,
        settings: Settings | None = None,
        access_service: McpAccessService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.access_service = access_service or McpAccessService(self.settings)

    async def get_settings(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> McpIntegrationResponse:
        row = await self._get_row(session, user_id)
        api_key = row.api_key if row else None
        whitelist = await self.access_service.list_whitelist(session, user_id)
        blacklist = await self.access_service.list_blacklist(session, user_id)
        instance_allowed = self.access_service.instance_allowed_urls
        return McpIntegrationResponse(
            enabled=bool(row.enabled) if row else False,
            server_url=(row.server_url or "") if row else "",
            api_key_configured=bool(api_key),
            api_key_preview=mask_api_key(api_key),
            use_kubernetes=row.use_kubernetes if row else True,
            use_aws=row.use_aws if row else True,
            use_cloud_cost=row.use_cloud_cost if row else True,
            use_pr_reviewer=row.use_pr_reviewer if row else True,
            use_performance=row.use_performance if row else True,
            use_security=row.use_security if row else True,
            instance_server_configured=bool(self.settings.mcp_instance_server_url.strip()),
            instance_url_restrictions_enabled=self.access_service.instance_url_restrictions_enabled,
            instance_allowed_urls=instance_allowed,
            official_servers=list_official_mcp_servers(instance_allowed),
            whitelist=whitelist,
            blacklist=blacklist,
        )

    async def upsert_settings(
        self,
        session: AsyncSession,
        user_id: UUID,
        payload: McpIntegrationSettings,
    ) -> McpIntegrationResponse:
        row = await self._get_row(session, user_id)
        if row is None:
            row = UserMcpIntegration(user_id=user_id)
            session.add(row)

        server_url = payload.server_url.strip()
        if server_url:
            server_url = await self.access_service.validate_active_url(
                session,
                user_id,
                server_url,
            )

        row.enabled = payload.enabled
        row.server_url = server_url
        row.use_kubernetes = payload.use_kubernetes
        row.use_aws = payload.use_aws
        row.use_cloud_cost = payload.use_cloud_cost
        row.use_pr_reviewer = payload.use_pr_reviewer
        row.use_performance = payload.use_performance
        row.use_security = payload.use_security

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
    ) -> tuple[str | None, str | None]:
        """Return (server_url, api_key) when MCP should be used for this agent."""
        if user_id is not None:
            row = await self._get_row(session, user_id)
            if row and (row.enabled or not require_enabled):
                if not require_enabled or self._agent_enabled(row, agent_type):
                    url = (row.server_url or "").strip()
                    key = (row.api_key or "").strip() or None
                    if url:
                        validated = await self.access_service.validate_resolved_url(
                            session,
                            user_id,
                            url,
                        )
                        return validated, key

        instance_url = self.settings.mcp_instance_server_url.strip()
        if instance_url:
            instance_key = self.settings.mcp_instance_api_key.strip() or None
            if user_id is not None:
                validated = await self.access_service.validate_resolved_url(
                    session,
                    user_id,
                    instance_url,
                )
            else:
                validated = validate_mcp_url(
                    instance_url,
                    instance_allowed=self.access_service.instance_allowed_urls,
                    user_whitelist=[],
                    user_blacklist=[],
                    require_user_whitelist=False,
                )
            return validated, instance_key

        return None, None

    @staticmethod
    def _agent_enabled(row: UserMcpIntegration, agent_type: str) -> bool:
        normalized = agent_type.replace("-", "_")
        if normalized == "kubernetes":
            return row.use_kubernetes
        if normalized == "aws":
            return row.use_aws
        if normalized == "cloud_cost":
            return row.use_cloud_cost
        if normalized in {"pr_reviewer", "pr-reviewer"}:
            return row.use_pr_reviewer
        if normalized == "performance":
            return row.use_performance
        if normalized == "security":
            return row.use_security
        return True

    @staticmethod
    async def _get_row(
        session: AsyncSession,
        user_id: UUID,
    ) -> UserMcpIntegration | None:
        result = await session.execute(
            select(UserMcpIntegration).where(UserMcpIntegration.user_id == user_id)
        )
        return result.scalar_one_or_none()
