"""Boto3 session and client factory with optional STS AssumeRole."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from loguru import logger

from app.core.config import Settings, get_settings
from app.modules.aws.errors import AwsApiError, AwsCredentialsError


class AwsClientFactory:
    """Create boto3 clients for hub credentials or an assumed-role session."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        bound_credentials: dict[str, str] | None = None,
        assumed_account_id: str | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._bound_credentials = bound_credentials
        self.assumed_account_id = assumed_account_id

    def session(self, region: str) -> boto3.Session:
        if self._bound_credentials:
            return boto3.Session(region_name=region, **self._bound_credentials)

        session_kwargs: dict[str, Any] = {"region_name": region}
        profile = (self.settings.aws_profile or "").strip()
        if profile:
            session_kwargs["profile_name"] = profile
            return boto3.Session(**session_kwargs)

        # Docker env_file often sets AWS_PROFILE= with no value. Boto3 treats that
        # as a named profile and fails with "config profile () could not be found".
        saved_profile = os.environ.pop("AWS_PROFILE", None)
        if saved_profile is not None and not str(saved_profile).strip():
            saved_profile = None
        try:
            return boto3.Session(**session_kwargs)
        finally:
            if saved_profile is not None:
                os.environ["AWS_PROFILE"] = saved_profile

    def client(self, service_name: str, region: str) -> Any:
        return self.session(region).client(service_name)

    def resource(self, service_name: str, region: str) -> Any:
        return self.session(region).resource(service_name)

    def call(self, service_name: str, region: str, operation: str, **kwargs: Any) -> dict[str, Any]:
        client = self.client(service_name, region)
        try:
            method = getattr(client, operation)
            return method(**kwargs)
        except NoCredentialsError as exc:
            raise AwsCredentialsError(
                "AWS credentials not found. Configure AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY, "
                "AWS_PROFILE, or mount ~/.aws into the backend container."
            ) from exc
        except (ClientError, BotoCoreError) as exc:
            logger.warning(
                "AWS API call failed | service={} region={} operation={} error={}",
                service_name,
                region,
                operation,
                exc,
            )
            raise AwsApiError(str(exc)) from exc

    def get_caller_identity(self, region: str) -> dict[str, Any]:
        return self.call("sts", region, "get_caller_identity")

    def hub_account_id(self, region: str) -> str:
        identity = self.get_caller_identity(region)
        return str(identity["Account"])

    def for_assume_role(
        self,
        region: str,
        *,
        account_id: str,
        role_arn: str,
        external_id: str | None = None,
        session_duration: int = 3600,
    ) -> AwsClientFactory:
        """Return a factory bound to temporary credentials from STS AssumeRole."""
        hub = self if self._bound_credentials is None else AwsClientFactory(self.settings)
        sts = hub.client("sts", region)
        session_name = f"devops-open-agent-{account_id}"[:64]
        params: dict[str, Any] = {
            "RoleArn": role_arn,
            "RoleSessionName": session_name,
            "DurationSeconds": session_duration,
        }
        if external_id:
            params["ExternalId"] = external_id
        try:
            response = sts.assume_role(**params)
        except NoCredentialsError as exc:
            raise AwsCredentialsError(
                "AWS hub credentials not found; cannot AssumeRole into the target account."
            ) from exc
        except (ClientError, BotoCoreError) as exc:
            logger.warning(
                "STS AssumeRole failed | account={} role_arn={} error={}",
                account_id,
                role_arn,
                exc,
            )
            raise AwsApiError(f"Failed to assume role for account {account_id}: {exc}") from exc

        creds = response["Credentials"]
        bound = {
            "aws_access_key_id": creds["AccessKeyId"],
            "aws_secret_access_key": creds["SecretAccessKey"],
            "aws_session_token": creds["SessionToken"],
        }
        return AwsClientFactory(
            self.settings,
            bound_credentials=bound,
            assumed_account_id=account_id,
        )

    def for_account(
        self,
        region: str,
        account_id: str,
        *,
        role_arn: str | None = None,
        external_id: str | None = None,
        allow_hub: bool = True,
    ) -> AwsClientFactory:
        """
        Resolve a factory for the target account.

        - Hub identity matching account_id → base/hub factory
        - Otherwise require role_arn and AssumeRole
        """
        account_id = account_id.strip()
        hub = self if self._bound_credentials is None else AwsClientFactory(self.settings)
        try:
            hub_account = hub.hub_account_id(region)
        except AwsCredentialsError:
            raise
        except AwsApiError:
            raise

        if allow_hub and hub_account == account_id:
            return hub
        if not role_arn:
            raise AwsCredentialsError(
                f"Account {account_id} is not the hub account ({hub_account}) and no "
                "AssumeRole mapping is configured. Add it under Integrations → AWS Accounts."
            )
        assumed = hub.for_assume_role(
            region,
            account_id=account_id,
            role_arn=role_arn,
            external_id=external_id,
        )
        identity = assumed.get_caller_identity(region)
        assumed_account = str(identity["Account"])
        if assumed_account != account_id:
            raise AwsCredentialsError(
                f"Assumed role resolved to account {assumed_account}, expected {account_id}."
            )
        return assumed


@lru_cache
def get_aws_client_factory() -> AwsClientFactory:
    return AwsClientFactory()
