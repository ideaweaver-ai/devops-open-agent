"""Microsoft Teams delivery via incoming webhook."""

from __future__ import annotations

import httpx
from loguru import logger


class TeamsDeliveryError(Exception):
    """Raised when Teams message delivery fails."""


class TeamsClient:
    """Post MessageCard payloads to a Teams incoming webhook."""

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout

    async def post_webhook(self, webhook_url: str, payload: dict) -> None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(webhook_url, json=payload)
            if response.status_code not in {200, 202}:
                body = response.text[:200]
                raise TeamsDeliveryError(
                    f"Teams webhook failed ({response.status_code}): {body}"
                )
            if response.text.strip() == "1":
                return
            if response.text.strip() and response.text.strip() not in {"1", "OK", "ok"}:
                logger.debug("Teams webhook response | body={}", response.text[:200])
