"""Pydantic models for the AWS investigation engine."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.diagnosis import DiagnosisResult
from app.models.investigation import ObservabilityResult


CloudWatchWindow = Literal["1h", "24h", "7d"]

AwsIssueType = Literal[
    "full_scan",
    "ec2_availability",
    "lambda",
    "s3",
    "security",
    "network",
    "load_balancer",
    "performance",
    "change_audit",
]


class AwsInvestigationRequest(BaseModel):
    account_id: str = Field(..., description="Target AWS account ID")
    region: str = Field(..., description="Target AWS region")
    cloudwatch_window: CloudWatchWindow = "24h"
    issue_type: AwsIssueType = Field(
        default="full_scan",
        description="What kind of AWS issue to troubleshoot",
    )
    query: str | None = Field(
        default=None,
        description="Optional free-text description of the problem",
    )
    include_ai: bool = Field(
        default=True,
        description="Run LLM root cause analysis after evidence collection",
    )
    include_rag: bool = Field(
        default=False,
        description="Augment AI analysis with similar past investigations from Qdrant (RAG)",
    )


class AwsAccountInfo(BaseModel):
    account_id: str
    account_name: str | None = None
    enabled_regions: list[str] = Field(default_factory=list)
    credential_source: str = "default"
    caller_arn: str | None = None
    user_id: str | None = None


class AwsAccountSummary(BaseModel):
    account_id: str
    account_name: str | None = None


class AwsRegionInfo(BaseModel):
    region: str
    endpoint: str | None = None
    opt_in_status: str | None = None


class AwsEbsVolume(BaseModel):
    volume_id: str
    size_gb: int | None = None
    volume_type: str | None = None
    iops: int | None = None
    throughput: int | None = None
    state: str | None = None
    attached_instance_id: str | None = None
    device: str | None = None
    encrypted: bool | None = None


class AwsEc2Instance(BaseModel):
    instance_id: str
    name: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    instance_type: str | None = None
    private_ip: str | None = None
    public_ip: str | None = None
    ami_id: str | None = None
    subnet_id: str | None = None
    vpc_id: str | None = None
    security_groups: list[str] = Field(default_factory=list)
    iam_role: str | None = None
    auto_scaling_group: str | None = None
    volumes: list[AwsEbsVolume] = Field(default_factory=list)
    state: str | None = None
    state_transition_reason: str | None = None
    launch_time: str | None = None
    status_checks: dict[str, Any] = Field(default_factory=dict)


class AwsSubnet(BaseModel):
    subnet_id: str
    name: str | None = None
    vpc_id: str
    cidr_block: str | None = None
    availability_zone: str | None = None
    map_public_ip_on_launch: bool | None = None


class AwsRouteTable(BaseModel):
    route_table_id: str
    name: str | None = None
    vpc_id: str
    associated_subnet_ids: list[str] = Field(default_factory=list)
    routes: list[dict[str, Any]] = Field(default_factory=list)


class AwsInternetGateway(BaseModel):
    internet_gateway_id: str
    name: str | None = None
    vpc_ids: list[str] = Field(default_factory=list)
    state: str | None = None


class AwsNatGateway(BaseModel):
    nat_gateway_id: str
    name: str | None = None
    subnet_id: str | None = None
    vpc_id: str | None = None
    state: str | None = None
    public_ip: str | None = None


class AwsNetworkAcl(BaseModel):
    network_acl_id: str
    name: str | None = None
    vpc_id: str
    associated_subnet_ids: list[str] = Field(default_factory=list)
    is_default: bool | None = None


class AwsVpc(BaseModel):
    vpc_id: str
    name: str | None = None
    cidr_block: str | None = None
    is_default: bool | None = None
    state: str | None = None
    subnets: list[AwsSubnet] = Field(default_factory=list)
    route_tables: list[AwsRouteTable] = Field(default_factory=list)
    internet_gateways: list[AwsInternetGateway] = Field(default_factory=list)
    nat_gateways: list[AwsNatGateway] = Field(default_factory=list)
    network_acls: list[AwsNetworkAcl] = Field(default_factory=list)


class AwsSecurityGroupRule(BaseModel):
    protocol: str | None = None
    from_port: int | None = None
    to_port: int | None = None
    cidr_blocks: list[str] = Field(default_factory=list)
    source_security_group_id: str | None = None
    description: str | None = None


class AwsSecurityGroup(BaseModel):
    security_group_id: str
    name: str | None = None
    description: str | None = None
    vpc_id: str | None = None
    ingress_rules: list[AwsSecurityGroupRule] = Field(default_factory=list)
    egress_rules: list[AwsSecurityGroupRule] = Field(default_factory=list)
    attached_resource_ids: list[str] = Field(default_factory=list)


class AwsTargetHealth(BaseModel):
    target_id: str
    port: int | None = None
    health_state: str | None = None
    reason: str | None = None
    description: str | None = None


class AwsTargetGroup(BaseModel):
    target_group_arn: str
    target_group_name: str
    protocol: str | None = None
    port: int | None = None
    vpc_id: str | None = None
    load_balancer_arns: list[str] = Field(default_factory=list)
    targets: list[AwsTargetHealth] = Field(default_factory=list)


class AwsLoadBalancerListener(BaseModel):
    listener_arn: str
    protocol: str | None = None
    port: int | None = None
    rules: list[dict[str, Any]] = Field(default_factory=list)


class AwsLoadBalancer(BaseModel):
    load_balancer_arn: str
    name: str | None = None
    type: str | None = None
    scheme: str | None = None
    dns_name: str | None = None
    vpc_id: str | None = None
    security_groups: list[str] = Field(default_factory=list)
    availability_zones: list[str] = Field(default_factory=list)
    state: str | None = None
    listeners: list[AwsLoadBalancerListener] = Field(default_factory=list)
    target_group_arns: list[str] = Field(default_factory=list)


class AwsScalingActivity(BaseModel):
    activity_id: str
    status_code: str | None = None
    description: str | None = None
    cause: str | None = None
    start_time: str | None = None
    end_time: str | None = None


class AwsAutoScalingGroup(BaseModel):
    auto_scaling_group_name: str
    launch_template: str | None = None
    desired_capacity: int | None = None
    min_size: int | None = None
    max_size: int | None = None
    current_capacity: int | None = None
    instance_ids: list[str] = Field(default_factory=list)
    target_group_arns: list[str] = Field(default_factory=list)
    scaling_activities: list[AwsScalingActivity] = Field(default_factory=list)


class AwsElasticIp(BaseModel):
    allocation_id: str
    public_ip: str | None = None
    instance_id: str | None = None
    network_interface_id: str | None = None
    domain: str | None = None


class AwsLambdaEventSource(BaseModel):
    uuid: str
    event_source_arn: str | None = None
    event_source_type: str | None = None
    state: str | None = None
    batch_size: int | None = None


class AwsLambdaFunction(BaseModel):
    function_name: str
    function_arn: str
    runtime: str | None = None
    handler: str | None = None
    memory_size: int | None = None
    timeout: int | None = None
    state: str | None = None
    state_reason: str | None = None
    last_update_status: str | None = None
    role: str | None = None
    vpc_id: str | None = None
    subnet_ids: list[str] = Field(default_factory=list)
    security_group_ids: list[str] = Field(default_factory=list)
    environment_keys: list[str] = Field(default_factory=list)
    event_sources: list[AwsLambdaEventSource] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)
    description: str | None = None


class AwsS3BucketNotification(BaseModel):
    target_type: str
    target_arn: str | None = None
    events: list[str] = Field(default_factory=list)


class AwsS3Bucket(BaseModel):
    bucket_name: str
    region: str | None = None
    creation_date: str | None = None
    public_access_block: dict[str, bool | None] = Field(default_factory=dict)
    encryption_enabled: bool | None = None
    encryption_type: str | None = None
    versioning_status: str | None = None
    policy_is_public: bool | None = None
    logging_enabled: bool | None = None
    logging_target_bucket: str | None = None
    notifications: list[AwsS3BucketNotification] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)


class AwsResourceDiscoveryResult(BaseModel):
    ec2_instances: list[AwsEc2Instance] = Field(default_factory=list)
    lambda_functions: list[AwsLambdaFunction] = Field(default_factory=list)
    s3_buckets: list[AwsS3Bucket] = Field(default_factory=list)
    vpcs: list[AwsVpc] = Field(default_factory=list)
    security_groups: list[AwsSecurityGroup] = Field(default_factory=list)
    load_balancers: list[AwsLoadBalancer] = Field(default_factory=list)
    target_groups: list[AwsTargetGroup] = Field(default_factory=list)
    auto_scaling_groups: list[AwsAutoScalingGroup] = Field(default_factory=list)
    ebs_volumes: list[AwsEbsVolume] = Field(default_factory=list)
    elastic_ips: list[AwsElasticIp] = Field(default_factory=list)


class AwsTopologyRelationship(BaseModel):
    source: str
    target: str
    type: str
    region: str | None = None


class AwsTopologyGraphNode(BaseModel):
    id: str
    kind: str
    name: str
    region: str


class AwsTopologyResult(BaseModel):
    relationships: list[AwsTopologyRelationship] = Field(default_factory=list)
    nodes: list[str] = Field(default_factory=list)
    graph_nodes: list[AwsTopologyGraphNode] = Field(default_factory=list)


class AwsMetricSample(BaseModel):
    metric_name: str
    namespace: str
    dimensions: dict[str, str] = Field(default_factory=dict)
    window: str
    datapoints: list[dict[str, Any]] = Field(default_factory=list)
    unit: str | None = None


class AwsCloudWatchAlarm(BaseModel):
    alarm_name: str
    alarm_arn: str | None = None
    state_value: str | None = None
    state_reason: str | None = None
    metric_name: str | None = None
    namespace: str | None = None
    threshold: float | None = None
    comparison_operator: str | None = None


class AwsLambdaInvocationMetrics(BaseModel):
    function_name: str
    configured_timeout_sec: int | None = None
    errors: int = 0
    throttles: int = 0
    max_duration_ms: float | None = None
    avg_duration_ms: float | None = None
    timeout_log_events: int = 0
    duration_at_timeout: bool = False


class AwsCloudWatchResult(BaseModel):
    collected: bool = False
    window: str = "24h"
    metrics: list[AwsMetricSample] = Field(default_factory=list)
    lambda_metrics: list[AwsLambdaInvocationMetrics] = Field(default_factory=list)
    alarms: list[AwsCloudWatchAlarm] = Field(default_factory=list)
    error: str | None = None


class AwsCloudTrailEvent(BaseModel):
    event_id: str | None = None
    event_name: str | None = None
    event_time: str | None = None
    username: str | None = None
    principal_arn: str | None = None
    principal_type: str | None = None
    resource_type: str | None = None
    resource_name: str | None = None
    instance_ids: list[str] = Field(default_factory=list)
    security_group_ids: list[str] = Field(default_factory=list)
    rule_summary: str | None = None
    tag_summary: str | None = None
    source_ip: str | None = None
    user_agent: str | None = None
    read_only: bool | None = None
    error_code: str | None = None
    event_source: str | None = None


class AwsCloudTrailResult(BaseModel):
    collected: bool = False
    lookback_hours: int = 24
    events: list[AwsCloudTrailEvent] = Field(default_factory=list)
    instance_events: list[AwsCloudTrailEvent] = Field(default_factory=list)
    security_group_events: list[AwsCloudTrailEvent] = Field(default_factory=list)
    tracked_event_names: list[str] = Field(default_factory=list)
    error: str | None = None


class AwsConfigChange(BaseModel):
    resource_type: str | None = None
    resource_id: str | None = None
    capture_time: str | None = None
    configuration_state: dict[str, Any] = Field(default_factory=dict)


class AwsConfigResult(BaseModel):
    enabled: bool = False
    recorder_name: str | None = None
    recent_changes: list[AwsConfigChange] = Field(default_factory=list)
    error: str | None = None


class AwsDeploymentIntegrationStatus(BaseModel):
    enabled: bool = False


class AwsDeploymentCorrelationResult(BaseModel):
    enabled: bool = False
    github_actions: AwsDeploymentIntegrationStatus = Field(
        default_factory=AwsDeploymentIntegrationStatus
    )
    gitlab_ci: AwsDeploymentIntegrationStatus = Field(
        default_factory=AwsDeploymentIntegrationStatus
    )
    jenkins: AwsDeploymentIntegrationStatus = Field(
        default_factory=AwsDeploymentIntegrationStatus
    )
    aws_codepipeline: AwsDeploymentIntegrationStatus = Field(
        default_factory=AwsDeploymentIntegrationStatus
    )


class AwsInvestigationContext(BaseModel):
    account_id: str
    region: str
    collected_at: str
    issue_type: AwsIssueType = "full_scan"
    query: str | None = None
    resource_counts: dict[str, int] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class AwsInvestigationResponse(BaseModel):
    status: str
    account: AwsAccountInfo
    resources: AwsResourceDiscoveryResult
    topology: AwsTopologyResult
    cloudwatch: AwsCloudWatchResult
    cloudtrail: AwsCloudTrailResult
    aws_config: AwsConfigResult
    deployment_correlation: AwsDeploymentCorrelationResult
    observability: ObservabilityResult = Field(default_factory=ObservabilityResult)
    investigation: AwsInvestigationContext
    diagnosis: DiagnosisResult | None = None
    error: str | None = None


class AwsAccountsResponse(BaseModel):
    accounts: list[AwsAccountSummary]


class AwsRegionsResponse(BaseModel):
    account_id: str
    regions: list[AwsRegionInfo]
