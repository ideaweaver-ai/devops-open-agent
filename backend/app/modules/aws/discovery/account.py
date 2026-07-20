"""AWS account and region discovery."""

from __future__ import annotations

import asyncio
from uuid import UUID

from app.db.session import SessionLocal
from app.modules.aws.client import AwsClientFactory
from app.modules.aws.models import AwsAccountInfo, AwsAccountSummary, AwsRegionInfo
from app.services.aws_settings_service import AwsSettingsService


class AwsAccountDiscovery:
    def __init__(self, client_factory: AwsClientFactory | None = None) -> None:
        self.client_factory = client_factory or AwsClientFactory()
        self.aws_settings = AwsSettingsService()

    async def discover_account(self, region: str) -> AwsAccountInfo:
        return await asyncio.to_thread(self._discover_account_sync, region)

    def _discover_account_sync(self, region: str) -> AwsAccountInfo:
        identity = self.client_factory.get_caller_identity(region)
        account_id = identity["Account"]

        account_name = None
        try:
            iam = self.client_factory.client("iam", region)
            aliases = iam.list_account_aliases().get("AccountAliases") or []
            if aliases:
                account_name = aliases[0]
        except Exception:
            account_name = None

        ec2 = self.client_factory.client("ec2", region)
        regions_response = ec2.describe_regions(AllRegions=False)
        enabled_regions = sorted(
            item["RegionName"]
            for item in regions_response.get("Regions", [])
            if item.get("RegionName")
        )

        if self.client_factory.assumed_account_id:
            credential_source = "assume_role"
        elif self.client_factory.settings.aws_profile:
            credential_source = "profile"
        else:
            credential_source = "default"

        return AwsAccountInfo(
            account_id=account_id,
            account_name=account_name,
            enabled_regions=enabled_regions,
            credential_source=credential_source,
            caller_arn=identity.get("Arn"),
            user_id=identity.get("UserId"),
        )

    async def list_accounts(
        self,
        region: str,
        user_id: str | UUID | None = None,
    ) -> list[AwsAccountSummary]:
        hub = await self.discover_account(region)
        accounts = [
            AwsAccountSummary(
                account_id=hub.account_id,
                account_name=hub.account_name or hub.account_id,
            )
        ]
        seen = {hub.account_id}

        parsed_user = self._parse_user_id(user_id)
        if parsed_user is None:
            return accounts

        async with SessionLocal() as session:
            targets = await self.aws_settings.list_enabled_targets(
                session,
                parsed_user,
                require_integration_enabled=True,
            )
        for target in targets:
            if target.account_id in seen:
                continue
            accounts.append(
                AwsAccountSummary(
                    account_id=target.account_id,
                    account_name=target.label or target.account_id,
                )
            )
            seen.add(target.account_id)
        return accounts

    async def list_regions(
        self,
        account_id: str,
        region: str,
        user_id: str | UUID | None = None,
        client_factory: AwsClientFactory | None = None,
    ) -> list[AwsRegionInfo]:
        factory = client_factory or await self.resolve_factory(
            account_id,
            region,
            user_id=user_id,
        )
        discovery = AwsAccountDiscovery(factory)
        account = await discovery.discover_account(region)
        if account.account_id != account_id:
            return []
        return [AwsRegionInfo(region=name) for name in account.enabled_regions]

    async def resolve_factory(
        self,
        account_id: str,
        region: str,
        user_id: str | UUID | None = None,
        *,
        require_integration_enabled: bool = True,
    ) -> AwsClientFactory:
        hub = AwsClientFactory()
        account_id = account_id.strip()
        try:
            hub_account = await asyncio.to_thread(hub.hub_account_id, region)
        except Exception:
            hub_account = None

        if hub_account and hub_account == account_id:
            return hub

        parsed_user = self._parse_user_id(user_id)
        target = None
        if parsed_user is not None:
            async with SessionLocal() as session:
                target = await self.aws_settings.resolve_target(
                    session,
                    parsed_user,
                    account_id,
                    require_integration_enabled=require_integration_enabled,
                )
        if target is None or not target.role_arn:
            from app.modules.aws.errors import AwsCredentialsError

            raise AwsCredentialsError(
                f"Account {account_id} is not the hub account"
                + (f" ({hub_account})" if hub_account else "")
                + " and no AssumeRole mapping is configured. "
                "Add it under Integrations → AWS Accounts."
            )
        return await asyncio.to_thread(
            hub.for_account,
            target.default_region or region,
            account_id,
            role_arn=target.role_arn,
            external_id=target.external_id,
            allow_hub=False,
        )

    @staticmethod
    def _parse_user_id(user_id: str | UUID | None) -> UUID | None:
        if user_id is None:
            return None
        if isinstance(user_id, UUID):
            return user_id
        try:
            return UUID(str(user_id))
        except ValueError:
            return None
