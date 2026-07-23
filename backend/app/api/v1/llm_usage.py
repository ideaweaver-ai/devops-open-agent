"""LLM usage / cost dashboard API models and routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_current_user_record
from app.ai.pricing import (
    get_pricing_table,
    reset_pricing_table,
    runtime_pricing_path,
    save_pricing_table,
)
from app.db.models import User
from app.db.session import get_db_session
from app.models.auth import UserResponse
from app.services.audit_service import audit_service
from app.storage.factory import get_llm_usage_store

router = APIRouter(tags=["llm-usage"])


class LlmUsageTotals(BaseModel):
    call_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_usd: float = 0.0


class LlmUsageBucket(BaseModel):
    key: str
    call_count: int = 0
    total_tokens: int = 0
    estimated_usd: float = 0.0


class LlmUsageSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, ser_json_by_alias=True)

    from_date: str = Field(alias="from", serialization_alias="from")
    to_date: str = Field(alias="to", serialization_alias="to")
    totals: LlmUsageTotals
    by_day: list[LlmUsageBucket] = Field(default_factory=list)
    by_agent: list[LlmUsageBucket] = Field(default_factory=list)
    by_provider: list[LlmUsageBucket] = Field(default_factory=list)
    by_call_kind: list[LlmUsageBucket] = Field(default_factory=list)


class LlmUsageEvent(BaseModel):
    id: str
    created_at: str
    user_id: str | None = None
    scope_type: str
    scope_id: str
    agent_type: str | None = None
    provider: str
    model: str
    call_kind: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_usd: float | None = None


class LlmUsageEventsResponse(BaseModel):
    events: list[LlmUsageEvent] = Field(default_factory=list)


class LlmBudgetResponse(BaseModel):
    llm_daily_budget_usd: float | None = None
    today_estimated_usd: float = 0.0
    budget_alert_date: str | None = None


class LlmBudgetUpdateRequest(BaseModel):
    llm_daily_budget_usd: float | None = Field(
        default=None,
        description="Daily spend threshold in USD. Null or 0 disables alerts.",
    )


class ModelPricingRates(BaseModel):
    input_per_1m_usd: float = 0.0
    output_per_1m_usd: float = 0.0


class LlmPricingTableResponse(BaseModel):
    table: dict[str, dict[str, ModelPricingRates]]
    source_path: str


class LlmPricingTableUpdateRequest(BaseModel):
    table: dict[str, dict[str, ModelPricingRates]]


def _default_range() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
    return start.isoformat().replace("+00:00", "Z"), now.isoformat().replace("+00:00", "Z")


@router.get("/llm/usage/summary", response_model=LlmUsageSummaryResponse)
async def get_llm_usage_summary(
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    current_user: UserResponse = Depends(get_current_user),
) -> LlmUsageSummaryResponse:
    default_from, default_to = _default_range()
    store = get_llm_usage_store()
    await store.initialize()
    payload = await store.summarize(
        user_id=str(current_user.id),
        date_from=date_from or default_from,
        date_to=date_to or default_to,
    )

    return LlmUsageSummaryResponse.model_validate(
        {
            "from": payload["from"],
            "to": payload["to"],
            "totals": payload["totals"],
            "by_day": [
                {
                    "key": str(row.get("day") or "unknown"),
                    "call_count": int(row.get("call_count") or 0),
                    "total_tokens": int(row.get("total_tokens") or 0),
                    "estimated_usd": float(row.get("estimated_usd") or 0.0),
                }
                for row in payload["by_day"]
            ],
            "by_agent": [
                {
                    "key": str(row.get("agent_type") or "unknown"),
                    "call_count": int(row.get("call_count") or 0),
                    "total_tokens": int(row.get("total_tokens") or 0),
                    "estimated_usd": float(row.get("estimated_usd") or 0.0),
                }
                for row in payload["by_agent"]
            ],
            "by_provider": [
                {
                    "key": str(row.get("provider") or "unknown"),
                    "call_count": int(row.get("call_count") or 0),
                    "total_tokens": int(row.get("total_tokens") or 0),
                    "estimated_usd": float(row.get("estimated_usd") or 0.0),
                }
                for row in payload["by_provider"]
            ],
            "by_call_kind": [
                {
                    "key": str(row.get("call_kind") or "unknown"),
                    "call_count": int(row.get("call_count") or 0),
                    "total_tokens": int(row.get("total_tokens") or 0),
                    "estimated_usd": float(row.get("estimated_usd") or 0.0),
                }
                for row in payload["by_call_kind"]
            ],
        }
    )


@router.get("/llm/usage/events", response_model=LlmUsageEventsResponse)
async def list_llm_usage_events(
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    limit: int = Query(100, ge=1, le=500),
    current_user: UserResponse = Depends(get_current_user),
) -> LlmUsageEventsResponse:
    default_from, default_to = _default_range()
    store = get_llm_usage_store()
    await store.initialize()
    rows = await store.list_events(
        user_id=str(current_user.id),
        date_from=date_from or default_from,
        date_to=date_to or default_to,
        limit=limit,
    )
    return LlmUsageEventsResponse(events=[LlmUsageEvent(**row) for row in rows])


@router.get("/llm/usage/budget", response_model=LlmBudgetResponse)
async def get_llm_usage_budget(
    current_user: UserResponse = Depends(get_current_user),
    user: User = Depends(get_current_user_record),
) -> LlmBudgetResponse:
    today = datetime.now(timezone.utc).date().isoformat()
    store = get_llm_usage_store()
    await store.initialize()
    summary = await store.summarize(
        user_id=str(current_user.id),
        date_from=f"{today}T00:00:00Z",
        date_to=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    return LlmBudgetResponse(
        llm_daily_budget_usd=user.llm_daily_budget_usd,
        today_estimated_usd=float((summary.get("totals") or {}).get("estimated_usd") or 0.0),
        budget_alert_date=user.llm_budget_alert_date,
    )


@router.put("/llm/usage/budget", response_model=LlmBudgetResponse)
async def update_llm_usage_budget(
    payload: LlmBudgetUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user),
    user: User = Depends(get_current_user_record),
) -> LlmBudgetResponse:
    value = payload.llm_daily_budget_usd
    if value is not None and value < 0:
        raise HTTPException(status_code=400, detail="Budget must be null or >= 0.")
    if value is not None and value == 0:
        value = None
    user.llm_daily_budget_usd = value
    if value is None:
        user.llm_budget_alert_date = None
    await session.commit()
    await session.refresh(user)
    await audit_service.record(
        actor_user_id=str(current_user.id),
        actor_email=current_user.email,
        action="budget.updated",
        resource_type="llm_budget",
        resource_id=str(current_user.id),
        metadata={"llm_daily_budget_usd": value},
    )
    today = datetime.now(timezone.utc).date().isoformat()
    store = get_llm_usage_store()
    await store.initialize()
    summary = await store.summarize(
        user_id=str(current_user.id),
        date_from=f"{today}T00:00:00Z",
        date_to=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    return LlmBudgetResponse(
        llm_daily_budget_usd=user.llm_daily_budget_usd,
        today_estimated_usd=float((summary.get("totals") or {}).get("estimated_usd") or 0.0),
        budget_alert_date=user.llm_budget_alert_date,
    )

def _pricing_response(table: dict) -> LlmPricingTableResponse:
    return LlmPricingTableResponse(
        table=table,
        source_path=str(runtime_pricing_path()),
    )


@router.get("/llm/pricing", response_model=LlmPricingTableResponse)
async def get_llm_pricing(
    _current_user: UserResponse = Depends(get_current_user),
) -> LlmPricingTableResponse:
    return _pricing_response(get_pricing_table())


@router.put("/llm/pricing", response_model=LlmPricingTableResponse)
async def update_llm_pricing(
    payload: LlmPricingTableUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
) -> LlmPricingTableResponse:
    try:
        raw = {
            provider: {
                model: rates.model_dump()
                for model, rates in models.items()
            }
            for provider, models in payload.table.items()
        }
        saved = save_pricing_table(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await audit_service.record(
        actor_user_id=str(current_user.id),
        actor_email=current_user.email,
        action="pricing.updated",
        resource_type="pricing_table",
        resource_id="runtime",
        metadata={
            "providers": sorted(saved.keys()),
            "model_count": sum(len(models) for models in saved.values()),
        },
    )
    return _pricing_response(saved)


@router.post("/llm/pricing/reset", response_model=LlmPricingTableResponse)
async def reset_llm_pricing(
    current_user: UserResponse = Depends(get_current_user),
) -> LlmPricingTableResponse:
    saved = reset_pricing_table()
    await audit_service.record(
        actor_user_id=str(current_user.id),
        actor_email=current_user.email,
        action="pricing.updated",
        resource_type="pricing_table",
        resource_id="runtime",
        metadata={"reset_to_bundled": True, "providers": sorted(saved.keys())},
    )
    return _pricing_response(saved)

