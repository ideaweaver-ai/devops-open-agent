"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { formatUsageTokens, formatUsageUsd } from "@/components/LlmUsageBreakdown";
import { formatAgentType } from "@/lib/platform";
import { useInvestigationHistory } from "@/hooks/useInvestigationStatus";

function formatDate(value: string) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function statusBadgeClass(status: string) {
  switch (status) {
    case "success":
    case "completed":
    case "partial_success":
      return "border-emerald-500/20 bg-emerald-500/10 text-emerald-300";
    case "failed":
      return "border-red-500/20 bg-red-500/10 text-red-300";
    case "running":
      return "border-brand-500/20 bg-brand-500/10 text-brand-300";
    default:
      return "border-slate-500/20 bg-slate-500/10 text-slate-300";
  }
}

interface InvestigationHistoryProps {
  onSelect?: (investigationId: string) => void;
  agentFilter?: "kubernetes" | "aws" | "cloud_cost";
  scopeColumnLabel?: string;
  emptyStateHref?: string;
  emptyStateLabel?: string;
  backBasePath?: string;
}

export function InvestigationHistory({
  onSelect,
  agentFilter,
  scopeColumnLabel = "Cluster",
  emptyStateHref = "/",
  emptyStateLabel = "Run your first investigation",
  backBasePath = "/investigations",
}: InvestigationHistoryProps) {
  const router = useRouter();
  const { data, isLoading, isError } = useInvestigationHistory(agentFilter);

  const handleSelect = (investigationId: string) => {
    if (onSelect) {
      onSelect(investigationId);
      return;
    }
    router.push(`/investigations/${investigationId}?from=${encodeURIComponent(backBasePath)}`);
  };

  return (
    <div className="panel-accent p-6">
      <div className="mb-5 flex items-center justify-between gap-4 border-b border-white/[0.06] pb-4">
        <div>
          <p className="panel-subtitle mb-1">History</p>
          <h2 className="panel-title">Recent Investigations</h2>
        </div>
        {!isLoading && !isError && (data?.investigations.length ?? 0) > 0 && (
          <span className="rounded-full border border-white/[0.08] bg-slate-800/60 px-3 py-1 text-xs font-medium tabular-nums text-slate-400">
            {data?.investigations.length} total
          </span>
        )}
      </div>

      {isLoading && (
        <div className="flex items-center gap-2.5 text-sm text-slate-400">
          <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-brand-400" />
          Loading investigation history...
        </div>
      )}
      {isError && (
        <p className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          Unable to load investigation history. Is the backend running?
        </p>
      )}

      {!isLoading && !isError && (data?.investigations.length ?? 0) === 0 && (
        <div className="rounded-xl border border-dashed border-white/[0.08] bg-slate-950/30 px-6 py-10 text-center">
          <p className="text-sm text-slate-400">
            No investigations yet.{" "}
            <Link href={emptyStateHref} className="text-brand-400 hover:text-brand-300">
              {emptyStateLabel}
            </Link>
            .
          </p>
        </div>
      )}

      {!isLoading && !isError && (data?.investigations.length ?? 0) > 0 && (
        <div className="overflow-x-auto rounded-xl border border-white/[0.05]">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-white/[0.06] bg-slate-950/50">
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Root Cause
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Agent
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                  {scopeColumnLabel}
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Status
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Confidence
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Tokens
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Est. $
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Started
                </th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                  <span className="sr-only">View</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {data?.investigations.map((item, index) => (
                <tr
                  key={item.id}
                  onClick={() => handleSelect(item.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      handleSelect(item.id);
                    }
                  }}
                  tabIndex={0}
                  role="button"
                  className={`cursor-pointer border-b border-white/[0.04] text-slate-300 transition hover:bg-brand-500/5 focus:bg-brand-500/5 focus:outline-none ${
                    index % 2 === 0 ? "bg-transparent" : "bg-slate-950/20"
                  }`}
                >
                  <td className="max-w-xs px-4 py-3.5">
                    <span className="line-clamp-2 leading-relaxed">
                      {item.root_cause || "Investigation in progress / no RCA"}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <span
                      className={`inline-flex rounded-md border px-2 py-0.5 text-xs ${
                        item.agent_type === "aws"
                          ? "border-orange-500/15 bg-orange-500/10 text-orange-200"
                          : item.agent_type === "cloud_cost"
                            ? "border-emerald-500/15 bg-emerald-500/10 text-emerald-200"
                            : "border-brand-500/15 bg-brand-500/10 text-brand-200"
                      }`}
                    >
                      {formatAgentType(item.agent_type)}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <span className="inline-flex rounded-md border border-white/[0.08] bg-slate-800/50 px-2 py-0.5 font-mono text-xs text-slate-300">
                      {item.cluster_id}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <span
                      className={`status-pill border ${statusBadgeClass(item.status)}`}
                    >
                      {item.status}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 tabular-nums">
                    {item.confidence != null ? (
                      <span className="font-medium text-slate-200">{item.confidence}%</span>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3.5 tabular-nums text-slate-300">
                    {(item.llm_call_count ?? 0) > 0 ? (
                      formatUsageTokens(
                        (item.llm_input_tokens ?? 0) + (item.llm_output_tokens ?? 0),
                      )
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3.5 tabular-nums text-slate-300">
                    {(item.llm_call_count ?? 0) > 0 ? (
                      formatUsageUsd(item.llm_estimated_cost_usd)
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3.5 text-slate-400">
                    {formatDate(item.created_at)}
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <span className="text-xs font-medium text-brand-400">View →</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
