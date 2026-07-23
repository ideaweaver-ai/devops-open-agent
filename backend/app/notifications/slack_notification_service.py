"""Deliver AI recommendations to Slack."""

from __future__ import annotations

import asyncio
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.integrations.slack.client import SlackClient, SlackDeliveryError
from app.integrations.slack.formatter import (
    format_diagnosis_slack_payload,
    format_pr_review_slack_payload,
    format_test_slack_payload,
)
from app.models.diagnosis import DiagnosisResult
from app.services.slack_cooldown_service import SlackCooldownService
from app.services.slack_settings_service import SlackSettingsService


class SlackNotificationService:
    """Send investigation and PR review recommendations to Slack."""

    def __init__(
        self,
        settings_service: SlackSettingsService | None = None,
        cooldown_service: SlackCooldownService | None = None,
        client: SlackClient | None = None,
    ) -> None:
        self.settings_service = settings_service or SlackSettingsService()
        self.cooldown_service = cooldown_service or SlackCooldownService()
        self.client = client or SlackClient()
        self.settings = get_settings()

    def schedule_investigation_notification(
        self,
        *,
        investigation_id: str,
        agent_type: str,
        scope_label: str,
        diagnosis: DiagnosisResult | None,
        user_id: str | None,
    ) -> None:
        if diagnosis is None or not diagnosis.root_cause:
            return
        asyncio.create_task(
            self._notify_investigation(
                investigation_id=investigation_id,
                agent_type=agent_type,
                scope_label=scope_label,
                diagnosis=diagnosis,
                user_id=user_id,
            )
        )

    def schedule_pr_review_notification(
        self,
        *,
        review_id: str,
        owner: str,
        repository: str,
        pull_request_number: int,
        pull_request_title: str,
        overall_risk: str,
        final_recommendation: str,
        findings_count: int,
        user_id: str | None,
    ) -> None:
        if not final_recommendation:
            return
        asyncio.create_task(
            self._notify_pr_review(
                review_id=review_id,
                owner=owner,
                repository=repository,
                pull_request_number=pull_request_number,
                pull_request_title=pull_request_title,
                overall_risk=overall_risk,
                final_recommendation=final_recommendation,
                findings_count=findings_count,
                user_id=user_id,
            )
        )

    async def send_test_message(self, user_id: UUID) -> None:
        payload = format_test_slack_payload()
        async with SessionLocal() as session:
            webhook_url, channel = await self.settings_service.resolve_delivery(
                session,
                user_id,
                agent_type="kubernetes",
                require_enabled=False,
            )
        await self._deliver(webhook_url, channel, payload)

    async def _notify_investigation(
        self,
        *,
        investigation_id: str,
        agent_type: str,
        scope_label: str,
        diagnosis: DiagnosisResult,
        user_id: str | None,
    ) -> None:
        parsed_user_id = self._parse_user_id(user_id)
        app_url = self._investigation_url(agent_type, investigation_id)
        payload = format_diagnosis_slack_payload(
            agent_type=agent_type,
            scope_label=scope_label,
            investigation_id=investigation_id,
            diagnosis=diagnosis,
            app_url=app_url,
        )

        async with SessionLocal() as session:
            webhook_url, channel = await self.settings_service.resolve_delivery(
                session,
                parsed_user_id,
                agent_type=agent_type,
            )
            if not webhook_url and not channel:
                logger.debug(
                    "Slack notification skipped | no delivery configured | investigation_id={}",
                    investigation_id,
                )
                return

            if await self._skip_for_cooldown(session, parsed_user_id, investigation_id):
                return

            try:
                await self._deliver(webhook_url, channel, payload)
                await self.cooldown_service.mark_sent(session, parsed_user_id)
                logger.info(
                    "Slack investigation notification sent | id={} agent={}",
                    investigation_id,
                    agent_type,
                )
            except SlackDeliveryError as exc:
                logger.warning(
                    "Slack investigation notification failed | id={} error={}",
                    investigation_id,
                    exc,
                )

    async def _notify_pr_review(
        self,
        *,
        review_id: str,
        owner: str,
        repository: str,
        pull_request_number: int,
        pull_request_title: str,
        overall_risk: str,
        final_recommendation: str,
        findings_count: int,
        user_id: str | None,
    ) -> None:
        parsed_user_id = self._parse_user_id(user_id)
        app_url = self._pr_review_url(review_id)
        payload = format_pr_review_slack_payload(
            owner=owner,
            repository=repository,
            pull_request_number=pull_request_number,
            pull_request_title=pull_request_title,
            overall_risk=overall_risk,
            final_recommendation=final_recommendation,
            findings_count=findings_count,
            review_id=review_id,
            app_url=app_url,
        )

        async with SessionLocal() as session:
            webhook_url, channel = await self.settings_service.resolve_delivery(
                session,
                parsed_user_id,
                agent_type="pr_reviewer",
            )
            if not webhook_url and not channel:
                logger.debug(
                    "Slack PR notification skipped | no delivery configured | review_id={}",
                    review_id,
                )
                return

            if await self._skip_for_cooldown(session, parsed_user_id, review_id):
                return

            try:
                await self._deliver(webhook_url, channel, payload)
                await self.cooldown_service.mark_sent(session, parsed_user_id)
                logger.info("Slack PR review notification sent | id={}", review_id)
            except SlackDeliveryError as exc:
                logger.warning(
                    "Slack PR review notification failed | id={} error={}",
                    review_id,
                    exc,
                )

    async def _skip_for_cooldown(
        self,
        session: AsyncSession,
        user_id: UUID | None,
        reference_id: str,
    ) -> bool:
        remaining = await self.cooldown_service.seconds_until_send_allowed(session, user_id)
        if remaining <= 0:
            return False
        minutes = max(1, remaining // 60)
        logger.info(
            "Slack notification suppressed by cooldown | ref={} user={} retry_in_minutes≈{}",
            reference_id,
            user_id or "instance",
            minutes,
        )
        return True

    @staticmethod
    def _parse_user_id(user_id: str | None) -> UUID | None:
        if not user_id:
            return None
        try:
            return UUID(user_id)
        except ValueError:
            return None

    async def _deliver(
        self,
        webhook_url: str | None,
        channel: str | None,
        payload: dict,
    ) -> None:
        if webhook_url:
            await self.client.post_webhook(webhook_url, payload)
            return

        bot_token = self.settings.slack_bot_token.strip()
        if channel and bot_token:
            await self.client.post_channel_message(bot_token, channel, payload)
            return

        raise SlackDeliveryError("No Slack delivery method configured")

    def _investigation_url(self, agent_type: str, investigation_id: str) -> str:
        base = self.settings.public_app_url.rstrip("/")
        if not base:
            return ""
        if agent_type == "aws":
            return f"{base}/investigations/{investigation_id}?from=/aws/investigations"
        if agent_type == "cloud_cost":
            return (
                f"{base}/investigations/{investigation_id}"
                f"?from=/cloud-cost/investigations"
            )
        return f"{base}/investigations/{investigation_id}"

    def _pr_review_url(self, review_id: str) -> str:
        base = self.settings.public_app_url.rstrip("/")
        if not base:
            return ""
        return f"{base}/pr-reviewer/reviews/{review_id}"


slack_notification_service = SlackNotificationService()
