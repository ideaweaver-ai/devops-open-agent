from typing import Literal

from pydantic import BaseModel, Field

from app.models.diagnosis import DiagnosisResult


class KubectlResultModel(BaseModel):
    success: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    command: list[str] = Field(default_factory=list)
    error: str | None = None


class ClusterInfo(BaseModel):
    cluster_id: str
    name: str | None = None
    context: str | None = None
    version: str | None = None
    node_count: int = 0
    namespaces: list[str] = Field(default_factory=list)


class ResourceItem(BaseModel):
    name: str
    namespace: str
    uid: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)
    created_at: str | None = None
    metadata: dict = Field(default_factory=dict)


class ResourceDiscoveryResult(BaseModel):
    namespaces: list[ResourceItem] = Field(default_factory=list)
    deployments: list[ResourceItem] = Field(default_factory=list)
    replica_sets: list[ResourceItem] = Field(default_factory=list)
    pods: list[ResourceItem] = Field(default_factory=list)
    services: list[ResourceItem] = Field(default_factory=list)
    ingresses: list[ResourceItem] = Field(default_factory=list)
    config_maps: list[ResourceItem] = Field(default_factory=list)
    secrets: list[ResourceItem] = Field(default_factory=list)
    persistent_volumes: list[ResourceItem] = Field(default_factory=list)
    persistent_volume_claims: list[ResourceItem] = Field(default_factory=list)


class ProblematicPod(BaseModel):
    name: str
    namespace: str
    status: str
    reason: str | None = None
    message: str | None = None
    container_states: list[dict] = Field(default_factory=list)
    resource_ref: str


class PodInspectionResult(BaseModel):
    healthy: bool
    total_pods: int = 0
    problematic_pods: list[ProblematicPod] = Field(default_factory=list)


class PodLogEntry(BaseModel):
    pod: str
    namespace: str
    container: str | None = None
    lines: list[str] = Field(default_factory=list)
    matched_patterns: list[str] = Field(default_factory=list)
    resource_ref: str


class LogsCollectionResult(BaseModel):
    collected: bool = False
    pod_count: int = 0
    logs: list[PodLogEntry] = Field(default_factory=list)


class EventFinding(BaseModel):
    type: str
    reason: str
    message: str
    namespace: str
    involved_object: str
    count: int = 1
    last_timestamp: str | None = None


class EventsAnalysisResult(BaseModel):
    total_events: int = 0
    findings: list[EventFinding] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)


class DeploymentIssue(BaseModel):
    name: str
    namespace: str
    issue_type: str
    message: str
    desired_replicas: int = 0
    available_replicas: int = 0
    unavailable_replicas: int = 0
    resource_ref: str


class DeploymentInspectionResult(BaseModel):
    healthy: bool = True
    deployments_checked: int = 0
    issues: list[DeploymentIssue] = Field(default_factory=list)


class NetworkIssue(BaseModel):
    name: str
    namespace: str
    issue_type: str
    message: str
    resource_ref: str


class NetworkInspectionResult(BaseModel):
    healthy: bool = True
    services_checked: int = 0
    issues: list[NetworkIssue] = Field(default_factory=list)


class TopologyRelationship(BaseModel):
    source: str
    target: str
    type: str
    namespace: str | None = None


class TopologyGraphNode(BaseModel):
    id: str
    kind: str
    name: str
    namespace: str


class TopologyResult(BaseModel):
    relationships: list[TopologyRelationship] = Field(default_factory=list)
    nodes: list[str] = Field(default_factory=list)
    graph_nodes: list[TopologyGraphNode] = Field(default_factory=list)


class IntegrationStatus(BaseModel):
    enabled: bool = False
    error: str | None = None


class ObservabilityFinding(BaseModel):
    source: Literal["prometheus", "grafana"]
    title: str
    severity: str | None = None
    detail: str
    query: str | None = None
    timestamp: str | None = None


class ObservabilityResult(BaseModel):
    enabled: bool = False
    prometheus: IntegrationStatus = Field(default_factory=IntegrationStatus)
    grafana: IntegrationStatus = Field(default_factory=IntegrationStatus)
    loki: IntegrationStatus = Field(default_factory=IntegrationStatus)
    opentelemetry: IntegrationStatus = Field(default_factory=IntegrationStatus)
    findings: list[ObservabilityFinding] = Field(default_factory=list)
    summary: str | None = None


class DeploymentCorrelationResult(BaseModel):
    enabled: bool = False
    helm: IntegrationStatus = Field(default_factory=IntegrationStatus)
    argocd: IntegrationStatus = Field(default_factory=IntegrationStatus)
    github_actions: IntegrationStatus = Field(default_factory=IntegrationStatus)
    jenkins: IntegrationStatus = Field(default_factory=IntegrationStatus)


class InvestigationDetails(BaseModel):
    pods: PodInspectionResult
    logs: LogsCollectionResult
    events: EventsAnalysisResult
    deployments: DeploymentInspectionResult
    network: NetworkInspectionResult


class InvestigationResponse(BaseModel):
    status: str
    cluster: ClusterInfo
    resources: ResourceDiscoveryResult
    topology: TopologyResult
    observability: ObservabilityResult
    deployments: DeploymentCorrelationResult
    investigation: InvestigationDetails
    diagnosis: DiagnosisResult | None = None
    error: str | None = None
