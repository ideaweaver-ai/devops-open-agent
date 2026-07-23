"""Investigation job and history models."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.diagnosis import DiagnosisResult
from app.models.investigation import InvestigationResponse
from app.modules.aws.models import AwsInvestigationResponse
from app.modules.cloud_cost_detector.models.schemas import CloudCostInvestigationResponse


INVESTIGATION_STEPS = [
    "Cluster Discovery",
    "Resource Discovery",
    "Pod Inspection",
    "Log Collection",
    "Event Analysis",
    "Deployment Inspection",
    "Network Inspection",
    "Topology Extraction",
    "Observability Collection",
    "AI Diagnosis",
    "AI Verification",
]

AWS_INVESTIGATION_STEPS = [
    "Account Discovery",
    "EC2 Discovery",
    "Network Discovery",
    "Security Groups",
    "Load Balancers",
    "CloudWatch",
    "CloudTrail",
    "AWS Config",
    "Topology",
    "AI Diagnosis",
]

CLOUD_COST_INVESTIGATION_STEPS = [
    "Account Discovery",
    "Resource Discovery",
    "Unused Resource Analysis",
    "Cost Estimation",
    "AI Cost Analysis",
]


class InvestigationStartResponse(BaseModel):
    investigation_id: str
    status: str = "started"


class InvestigationStatusResponse(BaseModel):
    id: str
    status: str
    current_step: str | None = None
    progress_percentage: int = 0
    cluster_id: str | None = None
    error: str | None = None


class InvestigationHistoryItem(BaseModel):
    id: str
    cluster_id: str
    agent_type: str = "kubernetes"
    status: str
    created_at: datetime
    root_cause: str | None = None
    confidence: int | None = None
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    llm_estimated_cost_usd: float | None = None
    llm_call_count: int = 0


class InvestigationHistoryResponse(BaseModel):
    investigations: list[InvestigationHistoryItem] = Field(default_factory=list)


class InvestigationResultResponse(BaseModel):
    id: str
    status: str
    agent_type: str = "kubernetes"
    result: InvestigationResponse | None = None
    aws_result: AwsInvestigationResponse | None = None
    cloud_cost_result: CloudCostInvestigationResponse | None = None
    diagnosis: DiagnosisResult | None = None
    llm_usage: dict | None = None
    error: str | None = None
