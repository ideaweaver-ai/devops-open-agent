from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from app.core.errors import sanitize_error_message
from app.models.auth import UserResponse
from app.modules.aws.investigation_service import AWSInvestigationService
from app.modules.aws.models import (
    AwsAccountsResponse,
    AwsInvestigationRequest,
    AwsInvestigationResponse,
    AwsRegionsResponse,
    AwsTopologyResult,
)

router = APIRouter(tags=["aws-agent"])
aws_investigation_service = AWSInvestigationService()


class AwsAgentStatusResponse(BaseModel):
    agent: str = "aws"
    status: str = "available"
    message: str
    capabilities: list[str]


@router.get("/aws/status", response_model=AwsAgentStatusResponse)
async def get_aws_agent_status(
    _current_user: UserResponse = Depends(get_current_user),
) -> AwsAgentStatusResponse:
    return AwsAgentStatusResponse(
        message=(
            "AWS investigation engine collects infrastructure evidence via boto3, "
            "with optional STS AssumeRole for multi-account access."
        ),
        capabilities=[
            "ec2",
            "lambda",
            "s3",
            "vpc",
            "subnet",
            "security_groups",
            "route_tables",
            "nacls",
            "internet_gateways",
            "nat_gateways",
            "elastic_ips",
            "load_balancers",
            "target_groups",
            "auto_scaling_groups",
            "ebs",
            "cloudwatch",
            "cloudtrail",
            "aws_config",
            "topology",
            "ai_diagnosis",
            "multi_account_assume_role",
        ],
    )


@router.get("/aws/accounts", response_model=AwsAccountsResponse)
async def list_aws_accounts(
    region: str | None = Query(None, description="Region used for account discovery"),
    current_user: UserResponse = Depends(get_current_user),
) -> AwsAccountsResponse:
    settings = get_settings()
    target_region = region or settings.aws_default_region
    try:
        accounts = await aws_investigation_service.list_accounts(
            target_region,
            user_id=current_user.id,
        )
        return AwsAccountsResponse(accounts=accounts)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(exc))) from exc


@router.get("/aws/regions", response_model=AwsRegionsResponse)
async def list_aws_regions(
    account_id: str = Query(..., description="Target AWS account ID"),
    region: str | None = Query(None, description="Region used for discovery API calls"),
    current_user: UserResponse = Depends(get_current_user),
) -> AwsRegionsResponse:
    settings = get_settings()
    target_region = region or settings.aws_default_region
    try:
        regions = await aws_investigation_service.list_regions(
            account_id,
            target_region,
            user_id=current_user.id,
        )
        return AwsRegionsResponse(account_id=account_id, regions=regions)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(exc))) from exc


@router.get("/aws/topology", response_model=AwsTopologyResult)
async def get_aws_topology(
    account_id: str = Query(..., description="Target AWS account ID"),
    region: str = Query(..., description="AWS region to map"),
    current_user: UserResponse = Depends(get_current_user),
) -> AwsTopologyResult:
    try:
        return await aws_investigation_service.discover_topology(
            account_id,
            region,
            user_id=current_user.id,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(exc))) from exc


@router.post("/aws/investigate", response_model=AwsInvestigationResponse)
async def investigate_aws_infrastructure(
    request: AwsInvestigationRequest,
    current_user: UserResponse = Depends(get_current_user),
) -> AwsInvestigationResponse:
    result = await aws_investigation_service.investigate(
        request,
        user_id=str(current_user.id),
    )
    if result.status == "error":
        raise HTTPException(status_code=502, detail=result.error or "AWS investigation failed")
    return result
