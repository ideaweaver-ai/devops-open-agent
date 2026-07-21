"use client";

import Link from "next/link";
import axios from "axios";
import { DiagnosisCard } from "@/components/DiagnosisCard";
import { InvestigationProgress } from "@/components/InvestigationProgress";
import { AwsInvestigationResults } from "@/components/aws/AwsInvestigationResults";
import { formatLlmProviderLabel } from "@/components/LlmProviderBadge";
import { formatAgentType } from "@/lib/platform";
import { TopologyPlaceholder } from "@/components/TopologyPlaceholder";
import { ObservabilityEvidencePanel } from "@/components/ObservabilityEvidencePanel";
import {
  useInvestigationResult,
  useInvestigationStatus,
} from "@/hooks/useInvestigationStatus";
import type { InvestigationHistoryItem } from "@/types/investigation";
import { AWS_INVESTIGATION_STEPS, CLOUD_COST_INVESTIGATION_STEPS } from "@/types/investigation";
import type { AwsInvestigationResponse } from "@/types/aws";
import type { CloudCostInvestigationResponse } from "@/types/cloudCost";
import { CloudCostInvestigationResults } from "@/modules/cloud_cost_detector/CloudCostInvestigationResults";

const TERMINAL_STATUSES = new Set(["success", "partial_success", "completed", "failed"]);

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      return "Unable to reach the backend API.";
    }
    const detail = error.response.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "An unexpected error occurred.";
}

function formatDate(value: string) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

interface InvestigationDetailViewProps {
  investigationId: string;
  summary?: InvestigationHistoryItem | null;
  backHref?: string;
}

export function InvestigationDetailView({
  investigationId,
  summary,
  backHref = "/investigations",
}: InvestigationDetailViewProps) {
  const statusQuery = useInvestigationStatus(investigationId);
  const status = statusQuery.data?.status;
  const isTerminal = Boolean(status && TERMINAL_STATUSES.has(status));
  const resultQuery = useInvestigationResult(investigationId, isTerminal);

  const agentType = summary?.agent_type ?? resultQuery.data?.agent_type ?? "kubernetes";
  const isAws = agentType === "aws";
  const isCloudCost = agentType === "cloud_cost";

  const diagnosis =
    resultQuery.data?.diagnosis ??
    resultQuery.data?.result?.diagnosis ??
    resultQuery.data?.aws_result?.diagnosis ??
    resultQuery.data?.cloud_cost_result?.diagnosis ??
    null;
  const resultStatus = resultQuery.data?.status ?? status;
  const kubernetesResult = resultQuery.data?.result ?? null;
  const awsResult = (resultQuery.data?.aws_result ?? null) as AwsInvestigationResponse | null;
  const cloudCostResult = (resultQuery.data?.cloud_cost_result ??
    null) as CloudCostInvestigationResponse | null;

  const scopeId = summary?.cluster_id ?? statusQuery.data?.cluster_id ?? "—";
  const createdAt = summary?.created_at ? formatDate(summary.created_at) : null;
  const llmProviderLabel = formatLlmProviderLabel(diagnosis?.llm_provider);
  const agentLabel = formatAgentType(agentType);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Link
            href={backHref}
            className="mb-2 inline-flex items-center gap-1 text-sm text-slate-400 transition hover:text-brand-300"
          >
            ← Back to investigations
          </Link>
          <h2 className="panel-title">Investigation Details</h2>
          <p className="mt-1 font-mono text-xs text-slate-500">{investigationId}</p>
        </div>
      </div>

      <div className="panel-accent grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-6">
        <div>
          <p className="section-label">Agent</p>
          <p className="text-sm text-slate-200">{agentLabel}</p>
        </div>
        <div>
          <p className="section-label">{isAws || isCloudCost ? "Account / Region" : "Cluster"}</p>
          <p className="font-mono text-sm text-slate-200">{scopeId}</p>
        </div>
        <div>
          <p className="section-label">Status</p>
          <p className="text-sm capitalize text-slate-200">{status ?? "Loading..."}</p>
        </div>
        <div>
          <p className="section-label">AI Provider</p>
          <p className="text-sm text-slate-200">{llmProviderLabel ?? "—"}</p>
        </div>
        <div>
          <p className="section-label">Confidence</p>
          <p className="text-sm text-slate-200">
            {summary?.confidence != null ? `${summary.confidence}%` : "—"}
          </p>
        </div>
        <div>
          <p className="section-label">Started</p>
          <p className="text-sm text-slate-200">{createdAt ?? "—"}</p>
        </div>
      </div>

      {statusQuery.isLoading && (
        <div className="alert-loading flex items-center gap-3">
          <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-brand-500/30 border-t-brand-400" />
          Loading investigation...
        </div>
      )}

      {statusQuery.isError && (
        <div className="alert-error">
          Failed to load investigation status. {getErrorMessage(statusQuery.error)}
        </div>
      )}

      {statusQuery.data && !isTerminal && (
        <InvestigationProgress
          currentStep={statusQuery.data.current_step}
          progressPercentage={statusQuery.data.progress_percentage}
          status={statusQuery.data.status}
          steps={
            isAws
              ? AWS_INVESTIGATION_STEPS
              : isCloudCost
                ? CLOUD_COST_INVESTIGATION_STEPS
                : undefined
          }
          title={
            isAws
              ? "Investigating AWS Infrastructure..."
              : isCloudCost
                ? "Analyzing AWS Cost Optimization Opportunities..."
                : undefined
          }
        />
      )}

      {resultQuery.isLoading && isTerminal && (
        <div className="alert-loading flex items-center gap-3">
          <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-brand-500/30 border-t-brand-400" />
          Loading diagnosis...
        </div>
      )}

      {resultQuery.isError && (
        <div className="alert-error">
          Failed to load investigation result. {getErrorMessage(resultQuery.error)}
        </div>
      )}

      {isTerminal && (
        <>
          {!(isCloudCost && cloudCostResult?.analysis) && (
            <DiagnosisCard
              diagnosis={diagnosis}
              result={isAws ? undefined : kubernetesResult}
              status={resultStatus}
              errorMessage={resultQuery.data?.error ?? diagnosis?.llm_error}
              commandLabel={isAws || isCloudCost ? "AWS CLI Commands" : undefined}
            />
          )}
          {isAws && awsResult ? (
            <AwsInvestigationResults data={awsResult} />
          ) : isCloudCost && cloudCostResult ? (
            <CloudCostInvestigationResults data={cloudCostResult} />
          ) : (
            <>
              <ObservabilityEvidencePanel
                data={kubernetesResult?.observability}
                className="mb-6"
              />
              <TopologyPlaceholder
                relationships={kubernetesResult?.topology?.relationships ?? []}
              />
            </>
          )}
        </>
      )}
    </div>
  );
}
