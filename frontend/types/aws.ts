import type { DiagnosisResult } from "@/types/investigation";
import type { ObservabilityResult } from "@/types/observability";

export type CloudWatchWindow = "1h" | "24h" | "7d";

export type AwsIssueType =
  | "full_scan"
  | "ec2_availability"
  | "lambda"
  | "s3"
  | "security"
  | "network"
  | "load_balancer"
  | "performance"
  | "change_audit";

export interface AwsInvestigationRequest {
  account_id: string;
  region: string;
  cloudwatch_window?: CloudWatchWindow;
  issue_type?: AwsIssueType;
  query?: string | null;
  include_ai?: boolean;
}

export interface AwsAccountSummary {
  account_id: string;
  account_name?: string | null;
}

export interface AwsAccountInfo extends AwsAccountSummary {
  enabled_regions: string[];
  credential_source: string;
  caller_arn?: string | null;
  user_id?: string | null;
}

export interface AwsRegionInfo {
  region: string;
  endpoint?: string | null;
  opt_in_status?: string | null;
}

export interface AwsAccountsResponse {
  accounts: AwsAccountSummary[];
}

export interface AwsRegionsResponse {
  account_id: string;
  regions: AwsRegionInfo[];
}

export interface AwsEbsVolume {
  volume_id: string;
  size_gb?: number | null;
  volume_type?: string | null;
  iops?: number | null;
  throughput?: number | null;
  state?: string | null;
  attached_instance_id?: string | null;
  device?: string | null;
  encrypted?: boolean | null;
}

export interface AwsEc2Instance {
  instance_id: string;
  name?: string | null;
  tags?: Record<string, string>;
  instance_type?: string | null;
  private_ip?: string | null;
  public_ip?: string | null;
  ami_id?: string | null;
  subnet_id?: string | null;
  vpc_id?: string | null;
  security_groups: string[];
  iam_role?: string | null;
  auto_scaling_group?: string | null;
  volumes: AwsEbsVolume[];
  state?: string | null;
  state_transition_reason?: string | null;
  launch_time?: string | null;
  status_checks: Record<string, unknown>;
}

export interface AwsVpc {
  vpc_id: string;
  name?: string | null;
  cidr_block?: string | null;
  is_default?: boolean | null;
  state?: string | null;
  subnets: Array<{
    subnet_id: string;
    name?: string | null;
    vpc_id: string;
    cidr_block?: string | null;
    availability_zone?: string | null;
  }>;
  route_tables: Array<{
    route_table_id: string;
    name?: string | null;
    vpc_id: string;
    associated_subnet_ids: string[];
  }>;
  internet_gateways: Array<{ internet_gateway_id: string; name?: string | null }>;
  nat_gateways: Array<{ nat_gateway_id: string; name?: string | null; subnet_id?: string | null }>;
  network_acls: Array<{ network_acl_id: string; name?: string | null }>;
}

export interface AwsSecurityGroup {
  security_group_id: string;
  name?: string | null;
  description?: string | null;
  vpc_id?: string | null;
  ingress_rules: Array<Record<string, unknown>>;
  egress_rules: Array<Record<string, unknown>>;
  attached_resource_ids: string[];
}

export interface AwsLoadBalancer {
  load_balancer_arn: string;
  name?: string | null;
  type?: string | null;
  scheme?: string | null;
  dns_name?: string | null;
  vpc_id?: string | null;
  state?: string | null;
  target_group_arns: string[];
}

export interface AwsTargetGroup {
  target_group_arn: string;
  target_group_name: string;
  protocol?: string | null;
  port?: number | null;
  vpc_id?: string | null;
  targets: Array<{
    target_id: string;
    health_state?: string | null;
    reason?: string | null;
  }>;
}

export interface AwsAutoScalingGroup {
  auto_scaling_group_name: string;
  launch_template?: string | null;
  desired_capacity?: number | null;
  current_capacity?: number | null;
  instance_ids: string[];
  scaling_activities: Array<{
    activity_id: string;
    status_code?: string | null;
    description?: string | null;
    start_time?: string | null;
  }>;
}

export interface AwsLambdaEventSource {
  uuid: string;
  event_source_arn?: string | null;
  event_source_type?: string | null;
  state?: string | null;
  batch_size?: number | null;
}

export interface AwsLambdaFunction {
  function_name: string;
  function_arn: string;
  runtime?: string | null;
  handler?: string | null;
  memory_size?: number | null;
  timeout?: number | null;
  state?: string | null;
  state_reason?: string | null;
  last_update_status?: string | null;
  role?: string | null;
  vpc_id?: string | null;
  subnet_ids: string[];
  security_group_ids: string[];
  environment_keys: string[];
  event_sources: AwsLambdaEventSource[];
  tags?: Record<string, string>;
  description?: string | null;
}

export interface AwsS3BucketNotification {
  target_type: string;
  target_arn?: string | null;
  events: string[];
}

export interface AwsS3Bucket {
  bucket_name: string;
  region?: string | null;
  creation_date?: string | null;
  public_access_block: Record<string, boolean | null | undefined>;
  encryption_enabled?: boolean | null;
  encryption_type?: string | null;
  versioning_status?: string | null;
  policy_is_public?: boolean | null;
  logging_enabled?: boolean | null;
  logging_target_bucket?: string | null;
  notifications: AwsS3BucketNotification[];
  tags?: Record<string, string>;
}

export interface AwsResourceDiscoveryResult {
  ec2_instances: AwsEc2Instance[];
  lambda_functions: AwsLambdaFunction[];
  s3_buckets: AwsS3Bucket[];
  vpcs: AwsVpc[];
  security_groups: AwsSecurityGroup[];
  load_balancers: AwsLoadBalancer[];
  target_groups: AwsTargetGroup[];
  auto_scaling_groups: AwsAutoScalingGroup[];
  ebs_volumes: AwsEbsVolume[];
  elastic_ips: Array<{
    allocation_id: string;
    public_ip?: string | null;
    instance_id?: string | null;
  }>;
}

export interface AwsTopologyRelationship {
  source: string;
  target: string;
  type: string;
  region?: string | null;
}

export interface AwsTopologyGraphNode {
  id: string;
  kind: string;
  name: string;
  region: string;
}

export interface AwsTopologyResult {
  relationships: AwsTopologyRelationship[];
  nodes: string[];
  graph_nodes: AwsTopologyGraphNode[];
}

export interface AwsCloudWatchAlarm {
  alarm_name: string;
  state_value?: string | null;
  metric_name?: string | null;
  namespace?: string | null;
  threshold?: number | null;
}

export interface AwsLambdaInvocationMetrics {
  function_name: string;
  configured_timeout_sec?: number | null;
  errors?: number;
  throttles?: number;
  max_duration_ms?: number | null;
  avg_duration_ms?: number | null;
  timeout_log_events?: number;
  duration_at_timeout?: boolean;
}

export interface AwsCloudWatchResult {
  collected: boolean;
  window: string;
  metrics: Array<{
    metric_name: string;
    namespace: string;
    dimensions: Record<string, string>;
    window: string;
    datapoints: Array<Record<string, unknown>>;
  }>;
  lambda_metrics?: AwsLambdaInvocationMetrics[];
  alarms: AwsCloudWatchAlarm[];
  error?: string | null;
}

export interface AwsCloudTrailEvent {
  event_id?: string | null;
  event_name?: string | null;
  event_time?: string | null;
  username?: string | null;
  principal_arn?: string | null;
  principal_type?: string | null;
  resource_type?: string | null;
  resource_name?: string | null;
  instance_ids?: string[];
  tag_summary?: string | null;
  source_ip?: string | null;
  user_agent?: string | null;
  error_code?: string | null;
}

export interface AwsCloudTrailResult {
  collected: boolean;
  lookback_hours: number;
  events: AwsCloudTrailEvent[];
  instance_events?: AwsCloudTrailEvent[];
  tracked_event_names: string[];
  error?: string | null;
}

export interface AwsConfigResult {
  enabled: boolean;
  recorder_name?: string | null;
  recent_changes: Array<{
    resource_type?: string | null;
    resource_id?: string | null;
    capture_time?: string | null;
  }>;
  error?: string | null;
}

export interface AwsDeploymentCorrelationResult {
  enabled: boolean;
}

export interface AwsInvestigationContext {
  account_id: string;
  region: string;
  collected_at: string;
  issue_type?: AwsIssueType;
  query?: string | null;
  resource_counts: Record<string, number>;
  notes: string[];
}

export interface AwsInvestigationResponse {
  status: string;
  account: AwsAccountInfo;
  resources: AwsResourceDiscoveryResult;
  topology: AwsTopologyResult;
  cloudwatch: AwsCloudWatchResult;
  cloudtrail: AwsCloudTrailResult;
  aws_config: AwsConfigResult;
  deployment_correlation: AwsDeploymentCorrelationResult;
  observability?: ObservabilityResult | null;
  investigation: AwsInvestigationContext;
  diagnosis?: DiagnosisResult | null;
  error?: string | null;
}
