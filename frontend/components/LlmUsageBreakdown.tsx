"use client";

import type { LlmUsageSummary } from "@/types/llmUsage";

function formatUsd(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  if (value === 0) {
    return "Free";
  }
  if (value < 0.01) {
    return `$${value.toFixed(4)}`;
  }
  return `$${value.toFixed(2)}`;
}

function formatTokens(value: number | null | undefined): string {
  if (value == null) {
    return "—";
  }
  return value.toLocaleString();
}

function formatCallKind(kind: string): string {
  return kind
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

interface LlmUsageBreakdownProps {
  usage?: LlmUsageSummary | null;
  className?: string;
}

export function LlmUsageBreakdown({ usage, className = "" }: LlmUsageBreakdownProps) {
  if (!usage || (usage.call_count ?? 0) === 0) {
    return null;
  }

  const calls = usage.calls ?? [];

  return (
    <div className={`panel-accent p-5 ${className}`.trim()}>
      <div className="mb-4 border-b border-white/[0.06] pb-3">
        <p className="panel-subtitle mb-1">LLM Usage</p>
        <h3 className="panel-title text-base">Tokens &amp; estimated cost</h3>
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-4">
        <div>
          <p className="section-label">Est. cost</p>
          <p className="text-sm font-semibold tabular-nums text-slate-900">
            {formatUsd(usage.estimated_usd)}
          </p>
        </div>
        <div>
          <p className="section-label">Total tokens</p>
          <p className="text-sm font-semibold tabular-nums text-slate-900">
            {formatTokens(usage.total_tokens)}
          </p>
        </div>
        <div>
          <p className="section-label">Input / Output</p>
          <p className="text-sm font-semibold tabular-nums text-slate-900">
            {formatTokens(usage.input_tokens)} / {formatTokens(usage.output_tokens)}
          </p>
        </div>
        <div>
          <p className="section-label">Calls</p>
          <p className="text-sm font-semibold tabular-nums text-slate-900">{usage.call_count}</p>
        </div>
      </div>

      {calls.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-white/[0.05]">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-white/[0.06] bg-slate-950/50">
                <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Kind
                </th>
                <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Provider / Model
                </th>
                <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Tokens
                </th>
                <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Est. $
                </th>
              </tr>
            </thead>
            <tbody>
              {calls.map((call, index) => (
                <tr
                  key={`${call.call_kind}-${call.model}-${index}`}
                  className={`border-b border-white/[0.04] text-slate-300 ${
                    index % 2 === 0 ? "bg-transparent" : "bg-slate-950/20"
                  }`}
                >
                  <td className="px-3 py-2.5">{formatCallKind(call.call_kind)}</td>
                  <td className="px-3 py-2.5">
                    <span className="text-slate-200">{call.provider}</span>
                    <span className="ml-1 font-mono text-xs text-slate-500">{call.model}</span>
                  </td>
                  <td className="px-3 py-2.5 tabular-nums">
                    {formatTokens(call.total_tokens)}
                    <span className="ml-1 text-xs text-slate-500">
                      ({formatTokens(call.input_tokens)} in / {formatTokens(call.output_tokens)} out)
                    </span>
                  </td>
                  <td className="px-3 py-2.5 tabular-nums">{formatUsd(call.estimated_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-3 text-xs text-slate-500">
        Costs are approximate from a static pricing table. Ollama is always $0.
      </p>
    </div>
  );
}

export function formatUsageUsd(value: number | null | undefined): string {
  return formatUsd(value);
}

export function formatUsageTokens(value: number | null | undefined): string {
  return formatTokens(value);
}
