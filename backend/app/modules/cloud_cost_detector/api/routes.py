"""Cloud Cost Detector API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from app.core.errors import sanitize_error_message
from app.models.auth import UserResponse
from app.modules.aws.errors import AwsApiError, AwsCredentialsError, AwsError
from app.modules.cloud_cost_detector.models.schemas import (
    CloudCostAccountResponse,
    CloudCostAnalyzeInventoryRequest,
    CloudCostAnalyzeInventoryResponse,
    CloudCostAnalyzeRequest,
    CloudCostAnalyzeResponse,
    CloudCostRegionsResponse,
)
from app.modules.cloud_cost_detector.services.discovery_service import CloudCostDiscoveryService

router = APIRouter(tags=["cloud-cost-detector"])
discovery_service = CloudCostDiscoveryService()


def _handle_aws_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AwsCredentialsError):
        # Use 503 (not 401) — the frontend treats 401 as JWT session expiry.
        return HTTPException(status_code=503, detail=sanitize_error_message(str(exc)))
    if isinstance(exc, AwsApiError):
        message = sanitize_error_message(str(exc))
        lowered = message.lower()
        if "accessdenied" in lowered or "access denied" in lowered or "unauthorized" in lowered:
            return HTTPException(status_code=403, detail=message)
        if "invalid" in lowered and "region" in lowered:
            return HTTPException(status_code=400, detail=message)
        return HTTPException(status_code=502, detail=message)
    if isinstance(exc, AwsError):
        return HTTPException(status_code=502, detail=sanitize_error_message(str(exc)))
    return HTTPException(status_code=502, detail=sanitize_error_message(str(exc)))


@router.get("/cloud-cost-detector/accounts", response_model=CloudCostAccountResponse)
async def get_cloud_cost_account(
    region: str | None = Query(None, description="Region used for STS/EC2 discovery calls"),
    _current_user: UserResponse = Depends(get_current_user),
) -> CloudCostAccountResponse:
    settings = get_settings()
    target_region = region or settings.aws_default_region
    try:
        return await discovery_service.get_account(target_region)
    except Exception as exc:
        raise _handle_aws_error(exc) from exc


@router.get("/cloud-cost-detector/regions", response_model=CloudCostRegionsResponse)
async def get_cloud_cost_regions(
    region: str | None = Query(None, description="Region used for EC2 describe_regions"),
    _current_user: UserResponse = Depends(get_current_user),
) -> CloudCostRegionsResponse:
    settings = get_settings()
    target_region = region or settings.aws_default_region
    try:
        regions = await discovery_service.list_regions(target_region)
        return CloudCostRegionsResponse(regions=regions)
    except Exception as exc:
        raise _handle_aws_error(exc) from exc


@router.post("/cloud-cost-detector/analyze", response_model=CloudCostAnalyzeResponse)
async def analyze_cloud_cost_resources(
    request: CloudCostAnalyzeRequest,
    _current_user: UserResponse = Depends(get_current_user),
) -> CloudCostAnalyzeResponse:
    try:
        return await discovery_service.analyze(request)
    except Exception as exc:
        raise _handle_aws_error(exc) from exc


@router.post(
    "/cloud-cost-detector/analyze-inventory",
    response_model=CloudCostAnalyzeInventoryResponse,
)
async def analyze_cloud_cost_inventory(
    request: CloudCostAnalyzeInventoryRequest,
    _current_user: UserResponse = Depends(get_current_user),
) -> CloudCostAnalyzeInventoryResponse:
    try:
        return await discovery_service.analyze_inventory(request)
    except Exception as exc:
        raise _handle_aws_error(exc) from exc
