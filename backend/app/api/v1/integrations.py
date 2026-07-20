"""Integration API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db_session
from app.integrations.mcp.client import McpClientError
from app.integrations.mcp.url_policy import McpUrlPolicyError
from app.integrations.pagerduty.client import PagerDutyDeliveryError
from app.integrations.slack.client import SlackDeliveryError
from app.integrations.teams.client import TeamsDeliveryError
from app.models.auth import UserResponse
from app.models.mcp_integration import (
    McpAskRequest,
    McpAskResponse,
    McpBlacklistCreate,
    McpBlacklistEntry,
    McpIntegrationResponse,
    McpIntegrationSettings,
    McpTestResponse,
    McpToolCallRecord,
    McpWhitelistCreate,
    McpWhitelistEntry,
)
from app.integrations.qdrant.client import QdrantError
from app.models.pagerduty_integration import (
    PagerDutyIntegrationResponse,
    PagerDutyIntegrationSettings,
    PagerDutyTestResponse,
)
from app.models.qdrant_integration import (
    QdrantIntegrationResponse,
    QdrantIntegrationSettings,
    QdrantTestResponse,
)
from app.models.slack_integration import (
    SlackIntegrationResponse,
    SlackIntegrationSettings,
    SlackTestResponse,
)
from app.models.teams_integration import (
    TeamsIntegrationResponse,
    TeamsIntegrationSettings,
    TeamsTestResponse,
)
from app.notifications.pagerduty_notification_service import pagerduty_notification_service
from app.notifications.slack_notification_service import slack_notification_service
from app.notifications.teams_notification_service import teams_notification_service
from app.services.mcp_settings_service import McpSettingsService
from app.services.mcp_ask_service import mcp_ask_service
from app.services.mcp_access_service import McpAccessService
from app.services.pagerduty_settings_service import PagerDutySettingsService
from app.services.qdrant_settings_service import QdrantSettingsService
from app.services.rag_service import rag_service
from app.services.slack_settings_service import SlackSettingsService
from app.services.teams_settings_service import TeamsSettingsService
from app.services.aws_settings_service import AwsSettingsService
from app.modules.aws.client import AwsClientFactory
from app.modules.aws.errors import AwsApiError, AwsCredentialsError
from app.core.config import get_settings
from app.models.aws_integration import (
    AwsIntegrationResponse,
    AwsIntegrationSettings,
    AwsTestRequest,
    AwsTestResponse,
)

router = APIRouter(tags=["integrations"])
slack_settings_service = SlackSettingsService()
pagerduty_settings_service = PagerDutySettingsService()
teams_settings_service = TeamsSettingsService()
aws_settings_service = AwsSettingsService()
mcp_settings_service = McpSettingsService()
mcp_access_service = McpAccessService()
qdrant_settings_service = QdrantSettingsService()


@router.get("/integrations/slack", response_model=SlackIntegrationResponse)
async def get_slack_integration(
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SlackIntegrationResponse:
    return await slack_settings_service.get_settings(session, current_user.id)


@router.put("/integrations/slack", response_model=SlackIntegrationResponse)
async def update_slack_integration(
    payload: SlackIntegrationSettings,
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SlackIntegrationResponse:
    if payload.enabled:
        if payload.delivery_method == "webhook":
            existing = await slack_settings_service.get_settings(session, current_user.id)
            has_webhook = bool(payload.webhook_url and payload.webhook_url.strip())
            if not has_webhook and not existing.webhook_url_configured:
                if not existing.instance_webhook_configured:
                    raise HTTPException(
                        status_code=400,
                        detail="Webhook URL is required when using webhook delivery.",
                    )
        elif payload.delivery_method == "channel":
            if not payload.channel.strip():
                raise HTTPException(
                    status_code=400,
                    detail="Slack channel is required when using channel delivery.",
                )
            existing = await slack_settings_service.get_settings(session, current_user.id)
            if not existing.instance_bot_configured:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "SLACK_BOT_TOKEN must be configured on the server "
                        "for channel delivery."
                    ),
                )

    return await slack_settings_service.upsert_settings(session, current_user.id, payload)


@router.post("/integrations/slack/test", response_model=SlackTestResponse)
async def test_slack_integration(
    current_user: UserResponse = Depends(get_current_user),
) -> SlackTestResponse:
    try:
        await slack_notification_service.send_test_message(current_user.id)
    except SlackDeliveryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SlackTestResponse(
        status="sent",
        message="Test message delivered to your configured Slack destination.",
    )


@router.get("/integrations/teams", response_model=TeamsIntegrationResponse)
async def get_teams_integration(
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TeamsIntegrationResponse:
    return await teams_settings_service.get_settings(session, current_user.id)


@router.put("/integrations/teams", response_model=TeamsIntegrationResponse)
async def update_teams_integration(
    payload: TeamsIntegrationSettings,
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TeamsIntegrationResponse:
    if payload.enabled:
        existing = await teams_settings_service.get_settings(session, current_user.id)
        has_webhook = bool(payload.webhook_url and payload.webhook_url.strip())
        if not has_webhook and not existing.webhook_url_configured:
            if not existing.instance_webhook_configured:
                raise HTTPException(
                    status_code=400,
                    detail="Teams webhook URL is required when notifications are enabled.",
                )

    return await teams_settings_service.upsert_settings(session, current_user.id, payload)


@router.post("/integrations/teams/test", response_model=TeamsTestResponse)
async def test_teams_integration(
    current_user: UserResponse = Depends(get_current_user),
) -> TeamsTestResponse:
    try:
        await teams_notification_service.send_test_message(current_user.id)
    except TeamsDeliveryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TeamsTestResponse(
        status="sent",
        message="Test message delivered to your configured Microsoft Teams channel.",
    )


@router.get("/integrations/pagerduty", response_model=PagerDutyIntegrationResponse)
async def get_pagerduty_integration(
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PagerDutyIntegrationResponse:
    return await pagerduty_settings_service.get_settings(session, current_user.id)


@router.put("/integrations/pagerduty", response_model=PagerDutyIntegrationResponse)
async def update_pagerduty_integration(
    payload: PagerDutyIntegrationSettings,
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PagerDutyIntegrationResponse:
    if payload.enabled:
        existing = await pagerduty_settings_service.get_settings(session, current_user.id)
        has_key = bool(payload.routing_key and payload.routing_key.strip())
        if not has_key and not existing.routing_key_configured:
            if not existing.instance_routing_key_configured:
                raise HTTPException(
                    status_code=400,
                    detail="PagerDuty routing key is required when notifications are enabled.",
                )

    return await pagerduty_settings_service.upsert_settings(session, current_user.id, payload)


@router.post("/integrations/pagerduty/test", response_model=PagerDutyTestResponse)
async def test_pagerduty_integration(
    current_user: UserResponse = Depends(get_current_user),
) -> PagerDutyTestResponse:
    try:
        await pagerduty_notification_service.send_test_message(current_user.id)
    except PagerDutyDeliveryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PagerDutyTestResponse(
        status="sent",
        message="Test incident delivered to your configured PagerDuty service.",
    )


@router.get("/integrations/qdrant", response_model=QdrantIntegrationResponse)
async def get_qdrant_integration(
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> QdrantIntegrationResponse:
    return await qdrant_settings_service.get_settings(session, current_user.id)


@router.put("/integrations/qdrant", response_model=QdrantIntegrationResponse)
async def update_qdrant_integration(
    payload: QdrantIntegrationSettings,
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> QdrantIntegrationResponse:
    if payload.enabled:
        existing = await qdrant_settings_service.get_settings(session, current_user.id)
        has_url = bool(payload.url.strip())
        if not has_url and not existing.url.strip() and not existing.instance_url_configured:
            raise HTTPException(
                status_code=400,
                detail="Qdrant URL is required when the integration is enabled.",
            )
    return await qdrant_settings_service.upsert_settings(session, current_user.id, payload)


@router.post("/integrations/qdrant/test", response_model=QdrantTestResponse)
async def test_qdrant_integration(
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> QdrantTestResponse:
    connection = await qdrant_settings_service.resolve_connection(
        session,
        current_user.id,
        agent_type="kubernetes",
        require_enabled=False,
    )
    if connection is None:
        raise HTTPException(
            status_code=400,
            detail="Configure a Qdrant URL before testing the connection.",
        )
    try:
        result = await rag_service.test_connection(connection)
    except QdrantError as exc:
        logger.warning("Qdrant test connection failed | error={}", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return QdrantTestResponse(
        status="ok",
        message="Connected to Qdrant and verified embeddings.",
        **result,
    )


@router.get("/integrations/mcp", response_model=McpIntegrationResponse)
async def get_mcp_integration(
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> McpIntegrationResponse:
    return await mcp_settings_service.get_settings(session, current_user.id)


@router.put("/integrations/mcp", response_model=McpIntegrationResponse)
async def update_mcp_integration(
    payload: McpIntegrationSettings,
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> McpIntegrationResponse:
    if payload.enabled:
        existing = await mcp_settings_service.get_settings(session, current_user.id)
        has_url = bool(payload.server_url.strip())
        has_user_url = bool(existing.server_url.strip())
        if not has_url and not has_user_url and not existing.instance_server_configured:
            raise HTTPException(
                status_code=400,
                detail="MCP server URL is required when the integration is enabled.",
            )
    try:
        return await mcp_settings_service.upsert_settings(session, current_user.id, payload)
    except McpUrlPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/integrations/mcp/test", response_model=McpTestResponse)
async def test_mcp_integration(
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> McpTestResponse:
    from app.integrations.mcp.client import McpClient

    server_url, api_key = await mcp_settings_service.resolve_connection(
        session,
        current_user.id,
        agent_type="kubernetes",
        require_enabled=False,
    )
    if not server_url:
        raise HTTPException(
            status_code=400,
            detail="Configure an MCP server URL before testing the connection.",
        )

    try:
        probe = await McpClient().probe_server(server_url, api_key)
    except McpClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except McpUrlPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"MCP connection failed: {exc}",
        ) from exc

    tool_names = [tool["name"] for tool in probe["tools"][:10]]
    return McpTestResponse(
        status="connected",
        message=(
            f"Connected to MCP server. Found {probe['tool_count']} tools "
            f"and {probe['resource_count']} resources."
        ),
        tool_count=probe["tool_count"],
        resource_count=probe["resource_count"],
        tools=tool_names,
    )


@router.post("/integrations/mcp/ask", response_model=McpAskResponse)
async def ask_mcp_integration(
    payload: McpAskRequest,
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> McpAskResponse:
    settings = await mcp_settings_service.get_settings(session, current_user.id)
    if not settings.enabled:
        raise HTTPException(
            status_code=400,
            detail="Enable MCP in settings before asking questions.",
        )

    try:
        result = await mcp_ask_service.ask(payload.question, current_user.id)
    except McpClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except McpUrlPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"MCP question failed: {exc}",
        ) from exc

    return McpAskResponse(
        answer=result["answer"],
        tools_used=[
            McpToolCallRecord.model_validate(record) for record in result["tools_used"]
        ],
    )


@router.post("/integrations/mcp/whitelist", response_model=McpWhitelistEntry)
async def add_mcp_whitelist_entry(
    payload: McpWhitelistCreate,
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> McpWhitelistEntry:
    try:
        return await mcp_access_service.add_whitelist_entry(
            session,
            current_user.id,
            payload,
        )
    except McpUrlPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/integrations/mcp/whitelist/{entry_id}", status_code=204)
async def delete_mcp_whitelist_entry(
    entry_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await mcp_access_service.remove_whitelist_entry(
            session,
            current_user.id,
            entry_id,
        )
    except McpUrlPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/integrations/mcp/blacklist", response_model=McpBlacklistEntry)
async def add_mcp_blacklist_entry(
    payload: McpBlacklistCreate,
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> McpBlacklistEntry:
    try:
        return await mcp_access_service.add_blacklist_entry(
            session,
            current_user.id,
            payload.server_url,
        )
    except McpUrlPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/integrations/mcp/blacklist/{entry_id}", status_code=204)
async def delete_mcp_blacklist_entry(
    entry_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await mcp_access_service.remove_blacklist_entry(
            session,
            current_user.id,
            entry_id,
        )
    except McpUrlPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/integrations/aws", response_model=AwsIntegrationResponse)
async def get_aws_integration(
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AwsIntegrationResponse:
    return await aws_settings_service.get_settings(session, current_user.id)


@router.put("/integrations/aws", response_model=AwsIntegrationResponse)
async def update_aws_integration(
    payload: AwsIntegrationSettings,
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AwsIntegrationResponse:
    if payload.enabled and not payload.accounts:
        raise HTTPException(
            status_code=400,
            detail="Add at least one AWS account with a role ARN when enabling multi-account.",
        )
    try:
        return await aws_settings_service.upsert_settings(session, current_user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/integrations/aws/test", response_model=AwsTestResponse)
async def test_aws_integration(
    payload: AwsTestRequest = AwsTestRequest(),
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AwsTestResponse:
    settings = get_settings()
    region = settings.aws_default_region or "us-east-1"
    targets = await aws_settings_service.list_enabled_targets(
        session,
        current_user.id,
        require_integration_enabled=False,
    )
    if not targets:
        raise HTTPException(
            status_code=400,
            detail="Configure at least one enabled AWS account before testing.",
        )
    requested = payload.account_id
    target = None
    if requested:
        target = next((t for t in targets if t.account_id == requested.strip()), None)
        if target is None:
            raise HTTPException(
                status_code=400,
                detail=f"No configured account found for account_id={requested}.",
            )
    else:
        target = targets[0]

    factory = AwsClientFactory()
    try:
        scoped = factory.for_account(
            target.default_region or region,
            target.account_id,
            role_arn=target.role_arn,
            external_id=target.external_id,
            allow_hub=False,
        )
        identity = scoped.get_caller_identity(target.default_region or region)
    except (AwsCredentialsError, AwsApiError) as exc:
        logger.warning("AWS AssumeRole test failed | account={} error={}", target.account_id, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AwsTestResponse(
        status="ok",
        message=f"Assumed role into account {target.account_id} successfully.",
        account_id=str(identity.get("Account")),
        caller_arn=identity.get("Arn"),
        assumed_role=True,
    )
