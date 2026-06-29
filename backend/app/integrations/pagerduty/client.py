"""PagerDuty Events API v2 delivery."""

from __future__ import annotations

import httpx
from loguru import logger

PAGERDUTY_EVENTS_URL = "https://events.pagerduty.com/v2/enqueue"


class PagerDutyDeliveryError(Exception):
    """Raised when PagerDuty event delivery fails."""


class PagerDutyClient:
    """Send events to PagerDuty via Events API v2."""

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout

    async def send_event(self, payload: dict) -> None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(PAGERDUTY_EVENTS_URL, json=payload)
            if response.status_code not in {200, 202}:
                body = response.text[:200]
                raise PagerDutyDeliveryError(
                    f"PagerDuty event failed ({response.status_code}): {body}"
                )
            data = response.json()
            status = data.get("status", "")
            if status not in {"success", "queued"}:
                logger.warning(
                    "PagerDuty unexpected response | status={} body={}",
                    status,
                    str(data)[:200],
                )
                raise PagerDutyDeliveryError(
                    f"PagerDuty unexpected status: {status or 'unknown'}"
                )
