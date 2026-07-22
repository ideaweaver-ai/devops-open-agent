from fastapi import APIRouter, Depends, HTTPException

from app.ai.bedrock_models import list_bedrock_text_models
from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from app.core.readiness import ReadinessService
from app.models.auth import UserResponse
from app.models.diagnosis import SystemInfoResponse
from app.models.readiness import SystemReadinessResponse
from pydantic import BaseModel, Field

router = APIRouter(tags=["system"])
readiness_service = ReadinessService()


class BedrockModelInfo(BaseModel):
    model_id: str
    model_name: str | None = None
    provider_name: str | None = None
    input_modalities: list[str] = Field(default_factory=list)
    output_modalities: list[str] = Field(default_factory=list)
    inference_types: list[str] = Field(default_factory=list)
    response_streaming: bool = False


class BedrockModelsResponse(BaseModel):
    region: str
    configured_model: str
    models: list[BedrockModelInfo]


@router.get("/system/info", response_model=SystemInfoResponse)
async def system_info(
    _current_user: UserResponse = Depends(get_current_user),
) -> SystemInfoResponse:
    settings = get_settings()
    return SystemInfoResponse(
        service=settings.service_name,
        environment=settings.app_env,
        llm_provider=settings.llm_provider,
        multi_cluster_enabled=settings.multi_cluster_enabled,
        topology_graph_enabled=settings.topology_graph_enabled,
        memory_enabled=settings.memory_enabled,
    )


@router.get("/system/readiness", response_model=SystemReadinessResponse)
async def system_readiness(
    _current_user: UserResponse = Depends(get_current_user),
) -> SystemReadinessResponse:
    checks = await readiness_service.check()
    return SystemReadinessResponse(**checks)


@router.get("/system/llm/bedrock/models", response_model=BedrockModelsResponse)
async def list_bedrock_models(
    _current_user: UserResponse = Depends(get_current_user),
) -> BedrockModelsResponse:
    """List Bedrock TEXT foundation models available to the configured AWS credentials."""
    settings = get_settings()
    region = (
        settings.bedrock_region.strip()
        or settings.aws_default_region.strip()
        or "us-west-2"
    )
    profile = settings.bedrock_aws_profile.strip() or settings.aws_profile.strip()
    try:
        models = await list_bedrock_text_models(region=region, aws_profile=profile)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Unable to list Bedrock models in {region}: {exc}",
        ) from exc
    return BedrockModelsResponse(
        region=region,
        configured_model=settings.bedrock_model,
        models=[BedrockModelInfo(**item) for item in models],
    )
