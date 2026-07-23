"""Helpers to attach usage sessions to investigation results."""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.ai.usage import UsageSession, UsageTracker
from app.storage.llm_usage_store import LlmUsageStore


def merge_usage_into_result(result: dict[str, Any], session: UsageSession | None) -> dict[str, Any]:
    if session is None or not session.calls:
        return result
    payload = dict(result)
    payload["llm_usage"] = session.summary_dict()
    return payload


async def persist_usage_session(
    usage_store: LlmUsageStore,
    session: UsageSession | None,
) -> None:
    if session is None or not session.calls:
        return
    await usage_store.record_session(session)
    try:
        from app.services.budget_alert_service import budget_alert_service

        await budget_alert_service.check_and_alert(session.user_id)
    except Exception:
        logger.exception("Budget alert check failed after usage persist")
