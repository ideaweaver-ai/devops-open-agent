"""Security Scanning API routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.auth.dependencies import get_current_user
from app.models.auth import UserResponse
from app.modules.security.models import (
    ScanType,
    SecurityScanDetailResponse,
    SecurityScanRequest,
    SecurityScanStartResponse,
    SecurityScanStatusResponse,
    ScanResult,
)
from app.modules.security.service import SecurityScanService
from app.modules.security.store import get_security_scan_store

router = APIRouter(tags=["security"])
scan_service = SecurityScanService()


@router.post("/security/scan", response_model=SecurityScanStartResponse)
async def start_security_scan(
    request: SecurityScanRequest,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
) -> SecurityScanStartResponse:
    if request.scan_type == ScanType.IMAGE and not request.image_name:
        raise HTTPException(
            status_code=422,
            detail="image_name is required for image scans",
        )

    scan_id = await scan_service.enqueue(
        request,
        user_id=str(current_user.id),
    )
    background_tasks.add_task(scan_service.process, scan_id, request)
    return SecurityScanStartResponse(
        scan_id=scan_id,
        status="queued",
        message="Security scan started",
    )


@router.get(
    "/security/scan/{scan_id}/status",
    response_model=SecurityScanStatusResponse,
)
async def get_scan_status(
    scan_id: str,
    _current_user: UserResponse = Depends(get_current_user),
) -> SecurityScanStatusResponse:
    store = get_security_scan_store()
    record = await store.get(scan_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Security scan not found")
    return SecurityScanStatusResponse(
        scan_id=record["scan_id"],
        status=record["status"],
        current_step=record.get("current_step"),
        progress_percentage=int(record.get("progress_percentage") or 0),
        error=record.get("error"),
    )


@router.get(
    "/security/scan/{scan_id}",
    response_model=SecurityScanDetailResponse,
)
async def get_scan_detail(
    scan_id: str,
    _current_user: UserResponse = Depends(get_current_user),
) -> SecurityScanDetailResponse:
    store = get_security_scan_store()
    record = await store.get(scan_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Security scan not found")

    result_data = record.get("result")
    result = ScanResult.model_validate(result_data) if result_data else None

    return SecurityScanDetailResponse(
        scan_id=record["scan_id"],
        agent_type=record.get("agent_type") or "security",
        status=record["status"],
        current_step=record.get("current_step"),
        progress_percentage=int(record.get("progress_percentage") or 0),
        error=record.get("error"),
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
        result=result,
    )
