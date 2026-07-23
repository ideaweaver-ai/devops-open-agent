"""Audit log API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.models.auth import UserResponse
from app.storage.factory import get_audit_store

router = APIRouter(tags=["audit"])


class AuditEvent(BaseModel):
    id: str
    created_at: str
    actor_user_id: str | None = None
    actor_email: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    metadata: dict[str, Any] | None = None


class AuditEventsResponse(BaseModel):
    events: list[AuditEvent] = Field(default_factory=list)


@router.get("/audit/events", response_model=AuditEventsResponse)
async def list_audit_events(
    action: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: UserResponse = Depends(get_current_user),
) -> AuditEventsResponse:
    store = get_audit_store()
    await store.initialize()
    rows = await store.list_events(
        actor_user_id=str(current_user.id),
        action=action,
        limit=limit,
    )
    return AuditEventsResponse(events=[AuditEvent.model_validate(row) for row in rows])
