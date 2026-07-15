"""Performance Debugging API routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.auth.dependencies import get_current_user
from app.models.auth import UserResponse
from app.modules.performance.models import (
    HostDebugResult,
    PerformanceDebugDetailResponse,
    PerformanceDebugHistoryItem,
    PerformanceDebugHistoryResponse,
    PerformanceDebugRequest,
    PerformanceDebugStartResponse,
    PerformanceDebugStatusResponse,
)
from app.modules.performance.service import PerformanceDebugService
from app.modules.performance.store import get_performance_debug_store

router = APIRouter(tags=["performance"])
debug_service = PerformanceDebugService()


def _to_host_results(record: dict) -> list[HostDebugResult]:
    return [HostDebugResult.model_validate(item) for item in record.get("hosts") or []]


@router.get("/performance/debug", response_model=PerformanceDebugHistoryResponse)
async def list_performance_debug_jobs(
    _current_user: UserResponse = Depends(get_current_user),
) -> PerformanceDebugHistoryResponse:
    store = get_performance_debug_store()
    records = await store.list_all()
    items = []
    for record in records:
        hosts = record.get("hosts") or []
        host_names = [h["host"] for h in hosts[:3]]
        suffix = f" +{len(hosts) - 3}" if len(hosts) > 3 else ""
        items.append(
            PerformanceDebugHistoryItem(
                debug_id=record["debug_id"],
                status=record["status"],
                host_count=len(hosts),
                hosts_summary=", ".join(host_names) + suffix,
                overall_summary=record.get("overall_summary"),
                created_at=record.get("created_at"),
            )
        )
    return PerformanceDebugHistoryResponse(jobs=items)


@router.post("/performance/debug", response_model=PerformanceDebugStartResponse)
async def start_performance_debug(
    request: PerformanceDebugRequest,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
) -> PerformanceDebugStartResponse:
    debug_id = await debug_service.enqueue(
        request.hosts,
        user_id=str(current_user.id),
    )
    background_tasks.add_task(debug_service.process, debug_id)
    return PerformanceDebugStartResponse(
        debug_id=debug_id,
        status="queued",
        message="Performance debugging started",
        host_count=len(request.hosts),
    )


@router.get("/performance/debug/{debug_id}/status", response_model=PerformanceDebugStatusResponse)
async def get_performance_debug_status(
    debug_id: str,
    _current_user: UserResponse = Depends(get_current_user),
) -> PerformanceDebugStatusResponse:
    store = get_performance_debug_store()
    record = await store.get(debug_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Performance debug job not found")
    return PerformanceDebugStatusResponse(
        debug_id=record["debug_id"],
        status=record["status"],
        current_step=record.get("current_step"),
        progress_percentage=int(record.get("progress_percentage") or 0),
        hosts=_to_host_results(record),
        error=record.get("error"),
    )


@router.get("/performance/debug/{debug_id}", response_model=PerformanceDebugDetailResponse)
async def get_performance_debug_detail(
    debug_id: str,
    _current_user: UserResponse = Depends(get_current_user),
) -> PerformanceDebugDetailResponse:
    store = get_performance_debug_store()
    record = await store.get(debug_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Performance debug job not found")
    return PerformanceDebugDetailResponse(
        debug_id=record["debug_id"],
        agent_type=record.get("agent_type") or "performance",
        status=record["status"],
        current_step=record.get("current_step"),
        progress_percentage=int(record.get("progress_percentage") or 0),
        hosts=_to_host_results(record),
        error=record.get("error"),
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
        overall_summary=record.get("overall_summary"),
    )
