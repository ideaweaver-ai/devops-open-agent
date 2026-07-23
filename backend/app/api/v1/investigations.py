from datetime import datetime
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from app.auth.dependencies import get_current_user
from app.core.errors import sanitize_error_message
from app.models.auth import UserResponse
from app.models.diagnosis import InvestigationRequest
from app.models.investigation_job import (
    InvestigationHistoryItem,
    InvestigationHistoryResponse,
    InvestigationResultResponse,
    InvestigationStartResponse,
    InvestigationStatusResponse,
)
from app.services.audit_service import audit_service
from app.services.investigation_job_service import InvestigationJobService

router = APIRouter(tags=["investigation"])
job_service = InvestigationJobService()


@router.post("/investigate", response_model=InvestigationStartResponse)
async def start_investigation(
    request: InvestigationRequest,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
) -> InvestigationStartResponse:
    investigation_id = await job_service.start_investigation(
        request,
        user_id=str(current_user.id),
    )
    background_tasks.add_task(job_service.run_investigation, investigation_id, request)
    await audit_service.record(
        actor_user_id=str(current_user.id),
        actor_email=current_user.email,
        action="investigation.started",
        resource_type="investigation",
        resource_id=investigation_id,
        metadata={
            "agent_type": request.agent_type,
            "cluster_id": request.cluster_id,
            "account_id": request.account_id,
            "region": request.region,
            "include_ai": request.include_ai,
        },
    )
    return InvestigationStartResponse(
        investigation_id=investigation_id,
        status="started",
    )


@router.get("/investigations", response_model=InvestigationHistoryResponse)
async def list_investigations(
    agent_type: str | None = Query(None, description="Filter by agent type, e.g. aws or kubernetes"),
    _current_user: UserResponse = Depends(get_current_user),
) -> InvestigationHistoryResponse:
    records = await job_service.list_history(agent_type=agent_type)
    investigations = [
        InvestigationHistoryItem(
            id=record["id"],
            cluster_id=record["cluster_id"],
            agent_type=record.get("agent_type") or "kubernetes",
            status=record["status"],
            created_at=datetime.fromisoformat(record["created_at"].replace("Z", "+00:00")),
            root_cause=record.get("root_cause"),
            confidence=record.get("confidence"),
            llm_input_tokens=int(record.get("llm_input_tokens") or 0),
            llm_output_tokens=int(record.get("llm_output_tokens") or 0),
            llm_estimated_cost_usd=record.get("llm_estimated_cost_usd"),
            llm_call_count=int(record.get("llm_call_count") or 0),
        )
        for record in records
    ]
    return InvestigationHistoryResponse(investigations=investigations)


@router.get("/investigations/{investigation_id}", response_model=InvestigationStatusResponse)
async def get_investigation_status(
    investigation_id: str,
    _current_user: UserResponse = Depends(get_current_user),
) -> InvestigationStatusResponse:
    record = await job_service.get_status(investigation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Investigation not found")

    return InvestigationStatusResponse(
        id=record["id"],
        status=record["status"],
        current_step=record.get("current_step"),
        progress_percentage=record.get("progress_percentage", 0),
        cluster_id=record.get("cluster_id"),
        error=sanitize_error_message(record["error"]) if record.get("error") else None,
    )


@router.get(
    "/investigations/{investigation_id}/result",
    response_model=InvestigationResultResponse,
)
async def get_investigation_result(
    investigation_id: str,
    _current_user: UserResponse = Depends(get_current_user),
) -> InvestigationResultResponse:
    record = await job_service.get_result(investigation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Investigation not found")

    status = record["status"]
    if status in {"running", "started"}:
        return InvestigationResultResponse(
            id=investigation_id,
            status=status,
            agent_type=record.get("agent_type") or "kubernetes",
            error="Investigation is still in progress",
        )

    agent_type = record.get("agent_type") or "kubernetes"
    llm_usage = None
    raw_result = record.get("result")
    if isinstance(raw_result, dict):
        llm_usage = raw_result.get("llm_usage")
    elif record.get("result_json"):
        try:
            parsed_json = json.loads(record["result_json"])
            if isinstance(parsed_json, dict):
                llm_usage = parsed_json.get("llm_usage")
        except (TypeError, ValueError, json.JSONDecodeError):
            llm_usage = None

    if agent_type == "aws":
        aws_result = InvestigationJobService.parse_aws_result(record)
        diagnosis = aws_result.diagnosis if aws_result else None
        return InvestigationResultResponse(
            id=investigation_id,
            status=status,
            agent_type=agent_type,
            aws_result=aws_result,
            diagnosis=diagnosis,
            llm_usage=llm_usage,
            error=sanitize_error_message(record["error"]) if record.get("error") else None,
        )

    if agent_type == "cloud_cost":
        cloud_cost_result = InvestigationJobService.parse_cloud_cost_result(record)
        diagnosis = cloud_cost_result.diagnosis if cloud_cost_result else None
        return InvestigationResultResponse(
            id=investigation_id,
            status=status,
            agent_type=agent_type,
            cloud_cost_result=cloud_cost_result,
            diagnosis=diagnosis,
            llm_usage=llm_usage,
            error=sanitize_error_message(record["error"]) if record.get("error") else None,
        )

    parsed = InvestigationJobService.parse_kubernetes_result(record)
    diagnosis = parsed.diagnosis if parsed else None

    return InvestigationResultResponse(
        id=investigation_id,
        status=status,
        agent_type=agent_type,
        result=parsed,
        diagnosis=diagnosis,
        llm_usage=llm_usage,
        error=sanitize_error_message(record["error"]) if record.get("error") else None,
    )


@router.post(
    "/investigations/{investigation_id}/rerun",
    response_model=InvestigationStartResponse,
)
async def rerun_investigation(
    investigation_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
) -> InvestigationStartResponse:
    request = await job_service.get_request_for_rerun(investigation_id)
    if not request:
        raise HTTPException(
            status_code=404,
            detail="Investigation not found or original parameters are unavailable for re-run.",
        )

    new_id = await job_service.start_investigation(
        request,
        user_id=str(current_user.id),
    )
    background_tasks.add_task(job_service.run_investigation, new_id, request)
    await audit_service.record(
        actor_user_id=str(current_user.id),
        actor_email=current_user.email,
        action="investigation.rerun",
        resource_type="investigation",
        resource_id=new_id,
        metadata={
            "source_investigation_id": investigation_id,
            "agent_type": request.agent_type,
            "cluster_id": request.cluster_id,
            "account_id": request.account_id,
            "region": request.region,
        },
    )
    return InvestigationStartResponse(
        investigation_id=new_id,
        status="started",
    )
