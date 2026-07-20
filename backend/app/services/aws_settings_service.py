"""Persist and load per-user AWS multi-account (AssumeRole) settings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserAwsAccount, UserAwsIntegration
from app.models.aws_integration import (
    AwsAccountResponse,
    AwsAccountSettings,
    AwsIntegrationResponse,
    AwsIntegrationSettings,
)
from app.services.mcp_settings_service import mask_api_key

_ACCOUNT_ID_RE = re.compile(r"^\d{12}$")
_ROLE_ARN_RE = re.compile(r"^arn:aws(-[a-z]+)*:iam::\d{12}:role/.+$")


@dataclass(frozen=True)
class AwsAccountTarget:
    account_id: str
    label: str
    role_arn: str | None = None
    external_id: str | None = None
    default_region: str | None = None
    is_hub: bool = False


class AwsSettingsService:
    """CRUD for user AWS multi-account preferences."""

    async def get_settings(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> AwsIntegrationResponse:
        integration = await self._get_integration(session, user_id)
        rows = await self._list_account_rows(session, user_id)
        return AwsIntegrationResponse(
            enabled=bool(integration.enabled) if integration else False,
            accounts=[self._to_account_response(row) for row in rows],
        )

    async def upsert_settings(
        self,
        session: AsyncSession,
        user_id: UUID,
        payload: AwsIntegrationSettings,
    ) -> AwsIntegrationResponse:
        self._validate_accounts(payload.accounts)

        integration = await self._get_integration(session, user_id)
        if integration is None:
            integration = UserAwsIntegration(user_id=user_id)
            session.add(integration)
        integration.enabled = payload.enabled

        existing_rows = await self._list_account_rows(session, user_id)
        existing_by_id = {str(row.id): row for row in existing_rows}
        keep_ids: set[str] = set()

        for item in payload.accounts:
            account_id = item.account_id.strip()
            role_arn = item.role_arn.strip()
            label = (item.label or "").strip() or account_id
            default_region = (item.default_region or "").strip() or None

            if item.id and item.id in existing_by_id:
                row = existing_by_id[item.id]
                keep_ids.add(item.id)
            else:
                row = UserAwsAccount(user_id=user_id)
                session.add(row)

            row.label = label
            row.account_id = account_id
            row.role_arn = role_arn
            row.default_region = default_region
            row.enabled = item.enabled
            if item.external_id is not None:
                row.external_id = item.external_id.strip() or None

        for row_id, row in existing_by_id.items():
            if row_id not in keep_ids:
                await session.delete(row)

        await session.commit()
        return await self.get_settings(session, user_id)

    async def list_enabled_targets(
        self,
        session: AsyncSession,
        user_id: UUID | None,
        *,
        require_integration_enabled: bool = True,
    ) -> list[AwsAccountTarget]:
        if user_id is None:
            return []
        integration = await self._get_integration(session, user_id)
        if require_integration_enabled and (integration is None or not integration.enabled):
            return []
        rows = await self._list_account_rows(session, user_id)
        return [
            AwsAccountTarget(
                account_id=row.account_id,
                label=row.label or row.account_id,
                role_arn=row.role_arn,
                external_id=row.external_id,
                default_region=row.default_region,
                is_hub=False,
            )
            for row in rows
            if row.enabled
        ]

    async def resolve_target(
        self,
        session: AsyncSession,
        user_id: UUID | None,
        account_id: str,
        *,
        require_integration_enabled: bool = True,
    ) -> AwsAccountTarget | None:
        account_id = account_id.strip()
        for target in await self.list_enabled_targets(
            session,
            user_id,
            require_integration_enabled=require_integration_enabled,
        ):
            if target.account_id == account_id:
                return target
        return None

    @staticmethod
    def _validate_accounts(accounts: list[AwsAccountSettings]) -> None:
        seen: set[str] = set()
        for item in accounts:
            account_id = item.account_id.strip()
            role_arn = item.role_arn.strip()
            if not _ACCOUNT_ID_RE.match(account_id):
                raise ValueError(f"Invalid AWS account ID: {account_id!r} (expected 12 digits).")
            if not _ROLE_ARN_RE.match(role_arn):
                raise ValueError(f"Invalid role ARN for account {account_id}.")
            # Role ARN account should match target account_id when present
            arn_account = role_arn.split(":")[4]
            if arn_account != account_id:
                raise ValueError(
                    f"Role ARN account {arn_account} does not match account_id {account_id}."
                )
            if account_id in seen:
                raise ValueError(f"Duplicate account_id in settings: {account_id}.")
            seen.add(account_id)

    @staticmethod
    def _to_account_response(row: UserAwsAccount) -> AwsAccountResponse:
        external = row.external_id
        return AwsAccountResponse(
            id=str(row.id),
            label=row.label or row.account_id,
            account_id=row.account_id,
            role_arn=row.role_arn,
            external_id_configured=bool(external),
            external_id_preview=mask_api_key(external),
            default_region=row.default_region or "",
            enabled=bool(row.enabled),
        )

    @staticmethod
    async def _get_integration(
        session: AsyncSession,
        user_id: UUID,
    ) -> UserAwsIntegration | None:
        result = await session.execute(
            select(UserAwsIntegration).where(UserAwsIntegration.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _list_account_rows(
        session: AsyncSession,
        user_id: UUID,
    ) -> list[UserAwsAccount]:
        result = await session.execute(
            select(UserAwsAccount)
            .where(UserAwsAccount.user_id == user_id)
            .order_by(UserAwsAccount.created_at.asc())
        )
        return list(result.scalars().all())
