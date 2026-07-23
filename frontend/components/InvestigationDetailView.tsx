"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import axios from "axios";
import { DiagnosisCard } from "@/components/DiagnosisCard";
import { InvestigationProgress } from "@/components/InvestigationProgress";
import { LlmUsageBreakdown } from "@/components/LlmUsageBreakdown";
import { AwsInvestigationResults } from "@/components/aws/AwsInvestigationResults";
import { formatLlmProviderLabel } from "@/components/LlmProviderBadge";
import { formatAgentType } from "@/lib/platform";
import {
  downloadInvestigationMarkdown,
  printInvestigationPdf,
} from "@/lib/investigationExport";
import { TopologyPlaceholder } from "@/components/TopologyPlaceholder";
import { ObservabilityEvidencePanel } from "@/components/ObservabilityEvidencePanel";
import {
  useInvestigationResult,
  useInvestigationStatus,
} from "@/hooks/useInvestigationStatus";
import { investigationApi } from "@/services/investigationApi";
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
  const router = useRouter();
  const [isRerunning, setIsRerunning] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [copyLinkLabel, setCopyLinkLabel] = useState("Copy link");

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

  const handleExportMarkdown = () => {
    if (!resultQuery.data) {
      return;
    }
    downloadInvestigationMarkdown(resultQuery.data, { scopeLabel: scopeId });
  };

  const handleExportPdf = () => {
    if (!resultQuery.data) {
      return;
    }
    printInvestigationPdf(resultQuery.data, { scopeLabel: scopeId });
  };

  const handleRerun = async () => {
    setActionError(null);
    setIsRerunning(true);
    try {
      const started = await investigationApi.rerunInvestigation(investigationId);
      router.push(
        `/investigations/${started.investigation_id}?from=${encodeURIComponent(backHref)}`,
      );
    } catch (error) {
      setActionError(getErrorMessage(error));
    } finally {
      setIsRerunning(false);
    }
  };

  const investigationDeepLink = () => {
    if (typeof window === "undefined") {
      return `/investigations/${investigationId}?from=${encodeURIComponent(backHref)}`;
    }
    const url = new URL(`/investigations/${investigationId}`, window.location.origin);
    url.searchParams.set("from", backHref);
    return url.toString();
  };

  const handleCopyLink = async () => {
    const link = investigationDeepLink();
    try {
      await navigator.clipboard.writeText(link);
      setCopyLinkLabel("Copied");
      window.setTimeout(() => setCopyLinkLabel("Copy link"), 2000);
    } catch {
      setActionError("Could not copy link to clipboard.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Link
            href={backHref}
            className="mb-2 inline-flex items-center gap-1 text-sm text-slate-600 transition hover:text-brand-700"
          >
            ← Back to investigations
          </Link>
          <h2 className="panel-title">Investigation Details</h2>
          <p className="mt-1 font-mono text-xs text-slate-500">{investigationId}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void handleCopyLink()}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 transition hover:bg-slate-50"
            title="Copy deep link for Slack, Teams, or email"
          >
            {copyLinkLabel}
          </button>
          {isTerminal && (
            <>
              <button
                type="button"
                onClick={handleExportMarkdown}
                disabled={!resultQuery.data}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 transition hover:bg-slate-50 disabled:opacity-50"
              >
                Export Markdown
              </button>
              <button
                type="button"
                onClick={handleExportPdf}
                disabled={!resultQuery.data}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 transition hover:bg-slate-50 disabled:opacity-50"
              >
                Export PDF
              </button>
              <button
                type="button"
                onClick={handleRerun}
                disabled={isRerunning}
                className="rounded-lg border border-brand-600 bg-brand-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-brand-500 disabled:opacity-50"
              >
                {isRerunning ? "Starting…" : "Re-run"}
              </button>
            </>
          )}
        </div>
      </div>

      {actionError && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {actionError}
        </p>
      )}

      <div className="panel-accent grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-6">
        <div>
          <p className="section-label">Agent</p>
          <p className="text-sm text-slate-800">{agentLabel}</p>
        </div>
        <div>
          <p className="section-label">{isAws || isCloudCost ? "Account / Region" : "Cluster"}</p>
          <p className="font-mono text-sm text-slate-800">{scopeId}</p>
        </div>
        <div>
          <p className="section-label">Status</p>
          <p className="text-sm capitalize text-slate-800">{status ?? "Loading..."}</p>
        </div>
        <div>
          <p className="section-label">AI Provider</p>
          <p className="text-sm text-slate-800">{llmProviderLabel ?? "—"}</p>
        </div>
        <div>
          <p className="section-label">Confidence</p>
          <p className="text-sm text-slate-800">
            {summary?.confidence != null ? `${summary.confidence}%` : "—"}
          </p>
        </div>
        <div>
          <p className="section-label">Started</p>
          <p className="text-sm text-slate-800">{createdAt ?? "—"}</p>
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
          <LlmUsageBreakdown
            usage={resultQuery.data?.llm_usage ?? resultQuery.data?.result?.llm_usage ?? null}
          />
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
