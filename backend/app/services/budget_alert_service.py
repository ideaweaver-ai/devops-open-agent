"""Notify Slack/Teams when a user's daily LLM spend hits their budget."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from loguru import logger
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import User
from app.db.session import SessionLocal
from app.integrations.slack.client import SlackDeliveryError
from app.integrations.teams.client import TeamsDeliveryError
from app.notifications.slack_notification_service import slack_notification_service
from app.notifications.teams_notification_service import teams_notification_service
from app.storage.factory import get_llm_usage_store


class BudgetAlertService:
    """Check daily spend against per-user budget and alert once per UTC day."""

    async def check_and_alert(self, user_id: str | None) -> None:
        if not user_id:
            return
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            return

        today = datetime.now(timezone.utc).date().isoformat()
        day_start = f"{today}T00:00:00Z"
        day_end = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        async with SessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_uuid))
            user = result.scalar_one_or_none()
            if user is None:
                return
            budget = user.llm_daily_budget_usd
            if budget is None or budget <= 0:
                return
            if user.llm_budget_alert_date == today:
                return

            store = get_llm_usage_store()
            await store.initialize()
            summary = await store.summarize(
                user_id=user_id,
                date_from=day_start,
                date_to=day_end,
            )
            spend = float((summary.get("totals") or {}).get("estimated_usd") or 0.0)
            if spend < float(budget):
                return

            settings = get_settings()
            base = (settings.public_app_url or "").rstrip("/")
            usage_url = f"{base}/usage" if base else "/usage"
            text = (
                f"LLM daily budget alert: spent ${spend:.4f} of ${float(budget):.2f} today (UTC). "
                f"Review usage: {usage_url}"
            )

            slack_ok = await self._notify_slack(session, user_uuid, text)
            teams_ok = await self._notify_teams(session, user_uuid, text)
            if slack_ok or teams_ok:
                user.llm_budget_alert_date = today
                await session.commit()
                logger.info(
                    "LLM budget alert sent | user_id={} spend={:.4f} budget={:.2f}",
                    user_id,
                    spend,
                    float(budget),
                )
            else:
                logger.warning(
                    "LLM budget crossed but no Slack/Teams delivery configured | "
                    "user_id={} spend={:.4f} budget={:.2f}",
                    user_id,
                    spend,
                    float(budget),
                )

    async def _notify_slack(self, session, user_id: UUID, text: str) -> bool:
        try:
            webhook_url, channel = await slack_notification_service.settings_service.resolve_delivery(
                session,
                user_id,
                "usage",
                require_enabled=True,
            )
            if not webhook_url and not channel:
                return False
            payload = {
                "text": text,
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": text},
                    }
                ],
            }
            await slack_notification_service._deliver(webhook_url, channel, payload)
            return True
        except SlackDeliveryError as exc:
            logger.warning("Slack budget alert failed | error={}", exc)
            return False
        except Exception:
            logger.exception("Unexpected Slack budget alert failure")
            return False

    async def _notify_teams(self, session, user_id: UUID, text: str) -> bool:
        try:
            webhook_url = await teams_notification_service.settings_service.resolve_webhook(
                session,
                user_id,
                "usage",
                require_enabled=True,
            )
            if not webhook_url:
                return False
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "summary": "LLM daily budget alert",
                "themeColor": "D97706",
                "title": "LLM daily budget alert",
                "text": text,
            }
            await teams_notification_service.client.post_webhook(webhook_url, payload)
            return True
        except TeamsDeliveryError as exc:
            logger.warning("Teams budget alert failed | error={}", exc)
            return False
        except Exception:
            logger.exception("Unexpected Teams budget alert failure")
            return False


budget_alert_service = BudgetAlertService()
