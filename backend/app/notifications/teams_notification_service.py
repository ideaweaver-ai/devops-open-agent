"""Deliver AI recommendations to Microsoft Teams."""

from __future__ import annotations

import asyncio
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.integrations.teams.client import TeamsClient, TeamsDeliveryError
from app.integrations.teams.formatter import (
    format_diagnosis_teams_payload,
    format_pr_review_teams_payload,
    format_test_teams_payload,
)
from app.models.diagnosis import DiagnosisResult
from app.services.teams_cooldown_service import TeamsCooldownService
from app.services.teams_settings_service import TeamsSettingsService


class TeamsNotificationService:
    """Send investigation and PR review recommendations to Microsoft Teams."""

    def __init__(
        self,
        settings_service: TeamsSettingsService | None = None,
        cooldown_service: TeamsCooldownService | None = None,
        client: TeamsClient | None = None,
    ) -> None:
        self.settings_service = settings_service or TeamsSettingsService()
        self.cooldown_service = cooldown_service or TeamsCooldownService()
        self.client = client or TeamsClient()
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
        payload = format_test_teams_payload()
        async with SessionLocal() as session:
            webhook_url = await self.settings_service.resolve_webhook(
                session,
                user_id,
                agent_type="kubernetes",
                require_enabled=False,
            )
        if not webhook_url:
            raise TeamsDeliveryError(
                "No Teams webhook configured. Add a webhook URL or ask your admin "
                "to set TEAMS_INSTANCE_WEBHOOK_URL."
            )
        await self.client.post_webhook(webhook_url, payload)

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
        payload = format_diagnosis_teams_payload(
            agent_type=agent_type,
            scope_label=scope_label,
            investigation_id=investigation_id,
            diagnosis=diagnosis,
            app_url=app_url,
        )

        async with SessionLocal() as session:
            webhook_url = await self.settings_service.resolve_webhook(
                session,
                parsed_user_id,
                agent_type=agent_type,
            )
            if not webhook_url:
                logger.debug(
                    "Teams notification skipped | no webhook configured | investigation_id={}",
                    investigation_id,
                )
                return

            if await self._skip_for_cooldown(session, parsed_user_id, investigation_id):
                return

            try:
                await self.client.post_webhook(webhook_url, payload)
                await self.cooldown_service.mark_sent(session, parsed_user_id)
                logger.info(
                    "Teams investigation notification sent | id={} agent={}",
                    investigation_id,
                    agent_type,
                )
            except TeamsDeliveryError as exc:
                logger.warning(
                    "Teams investigation notification failed | id={} error={}",
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
        payload = format_pr_review_teams_payload(
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
            webhook_url = await self.settings_service.resolve_webhook(
                session,
                parsed_user_id,
                agent_type="pr_reviewer",
            )
            if not webhook_url:
                logger.debug(
                    "Teams PR notification skipped | no webhook configured | review_id={}",
                    review_id,
                )
                return

            if await self._skip_for_cooldown(session, parsed_user_id, review_id):
                return

            try:
                await self.client.post_webhook(webhook_url, payload)
                await self.cooldown_service.mark_sent(session, parsed_user_id)
                logger.info("Teams PR review notification sent | id={}", review_id)
            except TeamsDeliveryError as exc:
                logger.warning(
                    "Teams PR review notification failed | id={} error={}",
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
            "Teams notification suppressed by cooldown | ref={} user={} retry_in_minutes≈{}",
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

    def _investigation_url(self, agent_type: str, investigation_id: str) -> str:
        base = self.settings.public_app_url.rstrip("/")
        if not base:
            return ""
        if agent_type == "aws":
            return f"{base}/aws/investigations/{investigation_id}"
        if agent_type == "cloud_cost":
            return f"{base}/cloud-cost/investigations/{investigation_id}"
        return f"{base}/investigations/{investigation_id}"

    def _pr_review_url(self, review_id: str) -> str:
        base = self.settings.public_app_url.rstrip("/")
        if not base:
            return ""
        return f"{base}/pr-reviewer/reviews/{review_id}"


teams_notification_service = TeamsNotificationService()
