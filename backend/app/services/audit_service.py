"""Fire-and-forget audit recording (never fails the main request)."""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.storage.audit_store import AuditStore
from app.storage.factory import get_audit_store

_SECRET_KEYS = {
    "webhook_url",
    "api_key",
    "token",
    "password",
    "secret",
    "bot_token",
    "routing_key",
    "authorization",
    "private_key",
    "access_key",
    "secret_key",
}


def redact_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not metadata:
        return None
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        lowered = key.lower()
        if any(part in lowered for part in _SECRET_KEYS):
            if value is None or value == "" or value is False:
                cleaned[key] = value
            else:
                cleaned[key] = "[redacted]"
        elif isinstance(value, dict):
            cleaned[key] = redact_metadata(value)
        else:
            cleaned[key] = value
    return cleaned


class AuditService:
    """Record audit events without raising to callers."""

    def __init__(self, store: AuditStore | None = None) -> None:
        self.store = store or get_audit_store()

    async def record(
        self,
        *,
        actor_user_id: str | None,
        actor_email: str | None,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            await self.store.initialize()
            await self.store.record(
                actor_user_id=actor_user_id,
                actor_email=actor_email,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata=redact_metadata(metadata),
            )
        except Exception:
            logger.exception(
                "Failed to record audit event | action={} resource_type={}",
                action,
                resource_type,
            )


audit_service = AuditService()
