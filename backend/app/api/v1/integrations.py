"""Integration API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db_session
from app.integrations.mcp.client import McpClientError
from app.integrations.pagerduty.client import PagerDutyDeliveryError
from app.integrations.slack.client import SlackDeliveryError
from app.integrations.teams.client import TeamsDeliveryError
from app.models.auth import UserResponse
from app.models.mcp_integration import (
    McpAskRequest,
    McpAskResponse,
    McpIntegrationResponse,
    McpIntegrationSettings,
    McpTestResponse,
    McpToolCallRecord,
)
from app.models.pagerduty_integration import (
    PagerDutyIntegrationResponse,
    PagerDutyIntegrationSettings,
    PagerDutyTestResponse,
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
from app.services.pagerduty_settings_service import PagerDutySettingsService
from app.services.slack_settings_service import SlackSettingsService
from app.services.teams_settings_service import TeamsSettingsService

router = APIRouter(tags=["integrations"])
slack_settings_service = SlackSettingsService()
pagerduty_settings_service = PagerDutySettingsService()
teams_settings_service = TeamsSettingsService()
mcp_settings_service = McpSettingsService()


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
    return await mcp_settings_service.upsert_settings(session, current_user.id, payload)


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
