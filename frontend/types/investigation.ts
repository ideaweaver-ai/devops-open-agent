export interface InvestigationStartResponse {
  investigation_id: string;
  status: string;
}

export interface InvestigationStatusResponse {
  id: string;
  status: string;
  current_step: string | null;
  progress_percentage: number;
  cluster_id?: string | null;
  error?: string | null;
}

export interface InvestigationHistoryItem {
  id: string;
  cluster_id: string;
  agent_type?: string;
  status: string;
  created_at: string;
  root_cause: string | null;
  confidence: number | null;
  llm_input_tokens?: number;
  llm_output_tokens?: number;
  llm_estimated_cost_usd?: number | null;
  llm_call_count?: number;
}

export interface InvestigationHistoryResponse {
  investigations: InvestigationHistoryItem[];
}

export interface DiagnosisEvidence {
  source: string;
  detail: string;
}

export interface PodIssueDiagnosis {
  pod: string;
  namespace: string;
  status: string;
  reason: string;
  root_cause: string;
  summary: string;
  evidence: DiagnosisEvidence[];
  suggested_fix: string;
  kubectl_commands: string[];
  validation_steps: string[];
  confidence_score: number;
}

export interface JudgeVerdict {
  verdict: "agree" | "partially_agree" | "disagree";
  confidence_score: number;
  reasoning: string;
  factual_issues: string[];
  missed_evidence: string[];
  command_safety_concerns: string[];
  suggested_improvements: string[];
  llm_provider?: string | null;
  llm_error?: string | null;
}

export interface DiagnosisResult {
  root_cause: string;
  summary: string;
  evidence: DiagnosisEvidence[];
  suggested_fix: string;
  kubectl_commands: string[];
  validation_steps: string[];
  prevention_recommendation: string;
  confidence_score: number;
  confidence_reason: string;
  needs_more_data: boolean;
  additional_data_needed: string[];
  issue_diagnoses?: PodIssueDiagnosis[];
  llm_provider?: string | null;
  llm_error?: string | null;
  judge_verdict?: JudgeVerdict | null;
}

export interface InvestigationResultResponse {
  id: string;
  status: string;
  agent_type?: string;
  result?: InvestigationPayload | null;
  aws_result?: import("@/types/aws").AwsInvestigationResponse | null;
  cloud_cost_result?: import("@/types/cloudCost").CloudCostInvestigationResponse | null;
  diagnosis?: DiagnosisResult | null;
  llm_usage?: import("@/types/llmUsage").LlmUsageSummary | null;
  error?: string | null;
}

export interface InvestigationPayload {
  status: string;
  cluster: Record<string, unknown>;
  resources: Record<string, unknown>;
  topology: {
    relationships: Array<{
      source: string;
      target: string;
      type: string;
      namespace?: string | null;
    }>;
    nodes: string[];
  };
  observability: import("@/types/observability").ObservabilityResult | Record<string, unknown>;
  deployments: Record<string, unknown>;
  investigation: Record<string, unknown>;
  diagnosis?: DiagnosisResult | null;
  llm_usage?: import("@/types/llmUsage").LlmUsageSummary | null;
  error?: string | null;
}

export interface StartInvestigationRequest {
  cluster_id?: string;
  include_ai?: boolean;
  include_rag?: boolean;
  include_judge?: boolean;
  judge_provider?: string | null;
  judge_model?: string | null;
  namespace?: string;
  agent_type?: "kubernetes" | "aws" | "cloud_cost";
  account_id?: string;
  region?: string;
  cloudwatch_window?: import("@/types/aws").CloudWatchWindow;
  issue_type?: import("@/types/aws").AwsIssueType;
  query?: string | null;
}

export const INVESTIGATION_STEPS = [
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
] as const;

export const AWS_INVESTIGATION_STEPS = [
  "Account Discovery",
  "EC2 Discovery",
  "Lambda Discovery",
  "S3 Discovery",
  "Network Discovery",
  "Security Groups",
  "Load Balancers",
  "Topology",
  "CloudWatch",
  "CloudTrail",
  "AWS Config",
  "Observability",
  "AI Diagnosis",
] as const;

export const CLOUD_COST_INVESTIGATION_STEPS = [
  "Account Discovery",
  "Resource Discovery",
  "Unused Resource Analysis",
  "Cost Estimation",
  "AI Cost Analysis",
] as const;

export const DEFAULT_CLUSTERS = [
  "prod-cluster",
  "staging-cluster",
  "dev-cluster",
  "kind-kind",
];
