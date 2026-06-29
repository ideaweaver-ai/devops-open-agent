"""Deliver AI recommendations to PagerDuty."""

from __future__ import annotations

import asyncio
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.integrations.pagerduty.client import PagerDutyClient, PagerDutyDeliveryError
from app.integrations.pagerduty.formatter import (
    format_diagnosis_event,
    format_pr_review_event,
    format_test_event,
)
from app.models.diagnosis import DiagnosisResult
from app.services.pagerduty_cooldown_service import PagerDutyCooldownService
from app.services.pagerduty_settings_service import PagerDutySettingsService


class PagerDutyNotificationService:
    """Send investigation and PR review recommendations to PagerDuty."""

    def __init__(
        self,
        settings_service: PagerDutySettingsService | None = None,
        cooldown_service: PagerDutyCooldownService | None = None,
        client: PagerDutyClient | None = None,
    ) -> None:
        self.settings_service = settings_service or PagerDutySettingsService()
        self.cooldown_service = cooldown_service or PagerDutyCooldownService()
        self.client = client or PagerDutyClient()
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
        async with SessionLocal() as session:
            routing_key = await self.settings_service.resolve_routing_key(
                session,
                user_id,
                agent_type="kubernetes",
                require_enabled=False,
            )
        if not routing_key:
            raise PagerDutyDeliveryError("No PagerDuty routing key configured")

        payload = format_test_event(routing_key=routing_key)
        await self.client.send_event(payload)

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

        async with SessionLocal() as session:
            routing_key = await self.settings_service.resolve_routing_key(
                session,
                parsed_user_id,
                agent_type=agent_type,
            )
            if not routing_key:
                logger.debug(
                    "PagerDuty notification skipped | no routing key | investigation_id={}",
                    investigation_id,
                )
                return

            if await self._skip_for_cooldown(session, parsed_user_id, investigation_id):
                return

            payload = format_diagnosis_event(
                routing_key=routing_key,
                agent_type=agent_type,
                scope_label=scope_label,
                investigation_id=investigation_id,
                diagnosis=diagnosis,
                app_url=app_url,
            )

            try:
                await self.client.send_event(payload)
                await self.cooldown_service.mark_sent(session, parsed_user_id)
                logger.info(
                    "PagerDuty investigation notification sent | id={} agent={}",
                    investigation_id,
                    agent_type,
                )
            except PagerDutyDeliveryError as exc:
                logger.warning(
                    "PagerDuty investigation notification failed | id={} error={}",
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

        async with SessionLocal() as session:
            routing_key = await self.settings_service.resolve_routing_key(
                session,
                parsed_user_id,
                agent_type="pr_reviewer",
            )
            if not routing_key:
                logger.debug(
                    "PagerDuty PR notification skipped | no routing key | review_id={}",
                    review_id,
                )
                return

            if await self._skip_for_cooldown(session, parsed_user_id, review_id):
                return

            payload = format_pr_review_event(
                routing_key=routing_key,
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

            try:
                await self.client.send_event(payload)
                await self.cooldown_service.mark_sent(session, parsed_user_id)
                logger.info("PagerDuty PR review notification sent | id={}", review_id)
            except PagerDutyDeliveryError as exc:
                logger.warning(
                    "PagerDuty PR review notification failed | id={} error={}",
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
            "PagerDuty notification suppressed by cooldown | ref={} user={} retry_in_minutes≈{}",
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


pagerduty_notification_service = PagerDutyNotificationService()
