"""AWS multi-account (STS AssumeRole) integration models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AwsAccountSettings(BaseModel):
    """One target account reachable via AssumeRole."""

    id: str | None = Field(
        default=None,
        description="Existing account row id; omit for new rows.",
    )
    label: str = Field(default="", description="Display name for the account.")
    account_id: str = Field(..., description="12-digit AWS account ID.")
    role_arn: str = Field(..., description="IAM role ARN to assume in the target account.")
    external_id: str | None = Field(
        default=None,
        description=(
            "Set to update the external ID; omit or null to keep existing; "
            "empty string to clear."
        ),
    )
    default_region: str | None = Field(
        default=None,
        description="Optional preferred region for this account.",
    )
    enabled: bool = True


class AwsAccountResponse(BaseModel):
    id: str
    label: str
    account_id: str
    role_arn: str
    external_id_configured: bool
    external_id_preview: str | None = None
    default_region: str
    enabled: bool


class AwsIntegrationSettings(BaseModel):
    enabled: bool = False
    accounts: list[AwsAccountSettings] = Field(default_factory=list)


class AwsIntegrationResponse(BaseModel):
    enabled: bool
    accounts: list[AwsAccountResponse]


class AwsTestRequest(BaseModel):
    account_id: str | None = Field(
        default=None,
        description="Target account to test; defaults to the first enabled account.",
    )


class AwsTestResponse(BaseModel):
    status: str
    message: str
    account_id: str | None = None
    caller_arn: str | None = None
    assumed_role: bool = False
