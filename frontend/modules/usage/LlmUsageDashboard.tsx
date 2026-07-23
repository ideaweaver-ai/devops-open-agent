"use client";

import { useEffect, useMemo, useState } from "react";
import {
  useLlmBudget,
  useLlmUsageEvents,
  useLlmUsageSummary,
  useUpdateLlmBudget,
} from "@/hooks/useLlmUsage";
import { formatAgentType } from "@/lib/platform";
import type { LlmUsageBucket } from "@/types/llmUsage";

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

function formatTokens(value: number): string {
  return value.toLocaleString();
}

function formatDate(value: string): string {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function formatDayLabel(value: string): string {
  try {
    const date = new Date(`${value}T12:00:00`);
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return value;
  }
}

function formatBucketLabel(key: string, kind: "agent" | "provider" | "kind" | "day"): string {
  if (kind === "agent") {
    return formatAgentType(key);
  }
  if (kind === "day") {
    return formatDayLabel(key);
  }
  return key;
}

type RangePreset = "7d" | "30d" | "90d" | "custom";

function toIsoStartOfDay(date: Date): string {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d.toISOString();
}

function toIsoNow(): string {
  return new Date().toISOString();
}

function toDateInputValue(iso: string): string {
  try {
    return new Date(iso).toISOString().slice(0, 10);
  } catch {
    return "";
  }
}

function rangeFromPreset(preset: Exclude<RangePreset, "custom">): { from: string; to: string } {
  const days = preset === "7d" ? 7 : preset === "30d" ? 30 : 90;
  const start = new Date();
  start.setDate(start.getDate() - (days - 1));
  return { from: toIsoStartOfDay(start), to: toIsoNow() };
}

const RANGE_OPTIONS: Array<{ id: RangePreset; label: string }> = [
  { id: "7d", label: "Last 7 days" },
  { id: "30d", label: "Last 30 days" },
  { id: "90d", label: "Last 90 days" },
  { id: "custom", label: "Custom" },
];

const CHART_COLORS = [
  "#2563eb",
  "#0891b2",
  "#059669",
  "#d97706",
  "#7c3aed",
  "#db2777",
];

function VerticalBarChart({
  title,
  rows,
  labelKind,
}: {
  title: string;
  rows: LlmUsageBucket[];
  labelKind: "day" | "agent" | "provider" | "kind";
}) {
  const maxTokens = Math.max(...rows.map((row) => row.total_tokens), 1);

  return (
    <div className="panel-accent p-5">
      <div className="mb-4 flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        <p className="text-xs text-slate-600">By tokens</p>
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-slate-600">No usage in this range.</p>
      ) : (
        <div className="flex h-48 items-end gap-2 sm:gap-3">
          {rows.map((row, index) => {
            const heightPct = Math.max(8, (row.total_tokens / maxTokens) * 100);
            const color = CHART_COLORS[index % CHART_COLORS.length];
            return (
              <div
                key={row.key}
                className="group flex min-w-0 flex-1 flex-col items-center justify-end gap-2"
              >
                <div className="rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-medium tabular-nums text-slate-800 opacity-100 shadow-sm sm:opacity-0 sm:group-hover:opacity-100">
                  {formatTokens(row.total_tokens)} · {formatUsd(row.estimated_usd)}
                </div>
                <div
                  className="w-full max-w-[3.5rem] rounded-t-md transition group-hover:brightness-110"
                  style={{
                    height: `${heightPct}%`,
                    background: `linear-gradient(180deg, ${color} 0%, ${color}cc 100%)`,
                    minHeight: "1.25rem",
                  }}
                  title={`${formatBucketLabel(row.key, labelKind)}: ${formatTokens(row.total_tokens)} tokens, ${formatUsd(row.estimated_usd)}`}
                />
                <p className="w-full truncate text-center text-[11px] font-medium text-slate-700">
                  {formatBucketLabel(row.key, labelKind)}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function HorizontalBarChart({
  title,
  rows,
  labelKind,
}: {
  title: string;
  rows: LlmUsageBucket[];
  labelKind: "agent" | "provider" | "kind";
}) {
  const maxTokens = Math.max(...rows.map((row) => row.total_tokens), 1);

  return (
    <div className="panel-accent p-5">
      <div className="mb-4 flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        <p className="text-xs text-slate-600">By tokens</p>
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-slate-600">No usage in this range.</p>
      ) : (
        <ul className="space-y-3">
          {rows.map((row, index) => {
            const widthPct = Math.max(6, (row.total_tokens / maxTokens) * 100);
            const color = CHART_COLORS[index % CHART_COLORS.length];
            return (
              <li key={row.key}>
                <div className="mb-1 flex items-center justify-between gap-3 text-sm">
                  <span className="truncate font-medium text-slate-800">
                    {formatBucketLabel(row.key, labelKind)}
                  </span>
                  <span className="shrink-0 tabular-nums text-slate-700">
                    {formatTokens(row.total_tokens)} · {formatUsd(row.estimated_usd)}
                  </span>
                </div>
                <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${widthPct}%`,
                      background: color,
                    }}
                  />
                </div>
                <p className="mt-1 text-[11px] text-slate-600">
                  {row.call_count} call{row.call_count === 1 ? "" : "s"}
                </p>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function LlmUsageDashboard() {
  const initialRange = useMemo(() => rangeFromPreset("30d"), []);
  const [preset, setPreset] = useState<RangePreset>("30d");
  const [fromDate, setFromDate] = useState(toDateInputValue(initialRange.from));
  const [toDate, setToDate] = useState(toDateInputValue(initialRange.to));

  const range = useMemo(() => {
    if (preset !== "custom") {
      return rangeFromPreset(preset);
    }
    const from = fromDate
      ? toIsoStartOfDay(new Date(`${fromDate}T00:00:00`))
      : initialRange.from;
    const to = toDate
      ? new Date(`${toDate}T23:59:59.999`).toISOString()
      : toIsoNow();
    return { from, to };
  }, [preset, fromDate, toDate, initialRange.from]);

  const summaryQuery = useLlmUsageSummary(true, range);
  const eventsQuery = useLlmUsageEvents(true, range);
  const budgetQuery = useLlmBudget();
  const updateBudget = useUpdateLlmBudget();
  const [budgetInput, setBudgetInput] = useState("");

  const summary = summaryQuery.data;
  const totals = summary?.totals;
  const budget = budgetQuery.data;

  useEffect(() => {
    if (!budget) {
      return;
    }
    setBudgetInput(
      budget.llm_daily_budget_usd != null ? String(budget.llm_daily_budget_usd) : "",
    );
  }, [budget?.llm_daily_budget_usd]);

  const selectPreset = (next: RangePreset) => {
    setPreset(next);
    if (next !== "custom") {
      const nextRange = rangeFromPreset(next);
      setFromDate(toDateInputValue(nextRange.from));
      setToDate(toDateInputValue(nextRange.to));
    }
  };

  const saveBudget = async () => {
    const trimmed = budgetInput.trim();
    const value = trimmed === "" ? null : Number(trimmed);
    if (value != null && (Number.isNaN(value) || value < 0)) {
      return;
    }
    await updateBudget.mutateAsync(value);
  };

  const todaySpend = budget?.today_estimated_usd ?? 0;
  const budgetLimit = budget?.llm_daily_budget_usd;
  const overBudget =
    budgetLimit != null && budgetLimit > 0 && todaySpend >= budgetLimit;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="panel-subtitle mb-1">Platform</p>
          <h1 className="panel-title">Cost / Usage</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-600">
            Token metering across investigations, judge, PR reviews, MCP Ask, and embeddings.
            Estimated spend uses the pricing table (editable under Usage → Pricing). Ollama is
            always $0.
          </p>
        </div>

        <div className="panel-accent w-full max-w-xl shrink-0 p-4 lg:w-auto">
          <p className="section-label mb-2">Time range</p>
          <div className="flex flex-wrap gap-2">
            {RANGE_OPTIONS.map((option) => {
              const active = preset === option.id;
              return (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => selectPreset(option.id)}
                  className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
                    active
                      ? "border-brand-600 bg-brand-600 text-white"
                      : "border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50"
                  }`}
                >
                  {option.label}
                </button>
              );
            })}
          </div>

          {preset === "custom" && (
            <div className="mt-3 grid grid-cols-2 gap-3">
              <label className="block text-xs font-medium text-slate-700">
                From
                <input
                  type="date"
                  value={fromDate}
                  max={toDate || undefined}
                  onChange={(event) => setFromDate(event.target.value)}
                  className="input-field mt-1 py-2 text-sm"
                />
              </label>
              <label className="block text-xs font-medium text-slate-700">
                To
                <input
                  type="date"
                  value={toDate}
                  min={fromDate || undefined}
                  onChange={(event) => setToDate(event.target.value)}
                  className="input-field mt-1 py-2 text-sm"
                />
              </label>
            </div>
          )}

          {summary && (
            <p className="mt-3 text-xs text-slate-600">
              Showing {formatDate(summary.from)} → {formatDate(summary.to)}
            </p>
          )}
        </div>
      </div>

      <div
        className={`panel-accent p-5 ${
          overBudget ? "border-amber-300 bg-amber-50" : ""
        }`}
      >
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Daily budget alert</h2>
            <p className="mt-1 text-sm text-slate-600">
              Warn via Slack/Teams once per UTC day when estimated spend reaches this threshold.
              Ollama usage is always $0 and will not trigger this alert — use a paid provider
              (e.g. OpenAI) to test.
            </p>
            <p className="mt-2 text-sm text-slate-800">
              Today (UTC): <span className="font-semibold tabular-nums">{formatUsd(todaySpend)}</span>
              {budgetLimit != null && budgetLimit > 0 && (
                <>
                  {" "}
                  / <span className="tabular-nums">{formatUsd(budgetLimit)}</span>
                </>
              )}
              {overBudget && (
                <span className="ml-2 font-semibold text-amber-800">Budget reached</span>
              )}
              {budgetLimit != null && budgetLimit > 0 && !overBudget && (
                <span className="ml-2 text-slate-600">
                  ({formatUsd(Math.max(0, budgetLimit - todaySpend))} remaining today)
                </span>
              )}
            </p>
          </div>
          <div className="flex flex-wrap items-end gap-2">
            <label className="block text-xs font-medium text-slate-700">
              Daily budget (USD)
              <input
                type="number"
                min="0"
                step="0.01"
                placeholder="e.g. 5.00"
                value={budgetInput}
                onChange={(event) => setBudgetInput(event.target.value)}
                className="input-field mt-1 w-40 py-2 text-sm"
              />
            </label>
            <button
              type="button"
              onClick={() => void saveBudget()}
              disabled={updateBudget.isPending}
              className="rounded-lg border border-brand-600 bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {updateBudget.isPending ? "Saving…" : "Save budget"}
            </button>
          </div>
        </div>
        {updateBudget.isError && (
          <p className="mt-3 text-sm text-red-700">Failed to save budget.</p>
        )}
        {updateBudget.isSuccess && (
          <p className="mt-3 text-sm text-emerald-700">Budget saved.</p>
        )}
      </div>

      {summaryQuery.isLoading && (
        <div className="flex items-center gap-2.5 text-sm text-slate-600">
          <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" />
          Loading usage summary...
        </div>
      )}

      {summaryQuery.isError && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          Unable to load usage summary. Is the backend running?
        </p>
      )}

      {totals && (
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="panel-accent p-5">
            <p className="section-label">Estimated spend</p>
            <p className="mt-1 text-3xl font-semibold tabular-nums tracking-tight text-slate-900">
              {formatUsd(totals.estimated_usd)}
            </p>
          </div>
          <div className="panel-accent p-5">
            <p className="section-label">Total tokens</p>
            <p className="mt-1 text-3xl font-semibold tabular-nums tracking-tight text-slate-900">
              {formatTokens(totals.total_tokens)}
            </p>
            <p className="mt-1 text-xs text-slate-600">
              {formatTokens(totals.input_tokens)} in / {formatTokens(totals.output_tokens)} out
            </p>
          </div>
          <div className="panel-accent p-5">
            <p className="section-label">LLM calls</p>
            <p className="mt-1 text-3xl font-semibold tabular-nums tracking-tight text-slate-900">
              {totals.call_count.toLocaleString()}
            </p>
          </div>
        </div>
      )}

      {summary && (
        <div className="grid gap-4 lg:grid-cols-2">
          <VerticalBarChart title="Spend by day" rows={summary.by_day} labelKind="day" />
          <HorizontalBarChart title="Spend by agent" rows={summary.by_agent} labelKind="agent" />
          <HorizontalBarChart
            title="Spend by provider"
            rows={summary.by_provider}
            labelKind="provider"
          />
          <HorizontalBarChart
            title="Spend by call kind"
            rows={summary.by_call_kind}
            labelKind="kind"
          />
        </div>
      )}

      <div className="panel-accent p-5">
        <div className="mb-4 border-b border-slate-200 pb-3">
          <h3 className="text-sm font-semibold text-slate-900">Recent events</h3>
        </div>
        {eventsQuery.isLoading && (
          <p className="text-sm text-slate-600">Loading events...</p>
        )}
        {eventsQuery.isError && (
          <p className="text-sm text-red-700">Unable to load usage events.</p>
        )}
        {!eventsQuery.isLoading &&
          !eventsQuery.isError &&
          (eventsQuery.data?.events.length ?? 0) === 0 && (
            <p className="text-sm text-slate-600">
              No metered LLM calls yet. Run an investigation to start tracking.
            </p>
          )}
        {(eventsQuery.data?.events.length ?? 0) > 0 && (
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-600">
                    When
                  </th>
                  <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Scope
                  </th>
                  <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Kind
                  </th>
                  <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Model
                  </th>
                  <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Tokens
                  </th>
                  <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Est. $
                  </th>
                </tr>
              </thead>
              <tbody>
                {eventsQuery.data?.events.map((event, index) => (
                  <tr
                    key={event.id}
                    className={`border-b border-slate-100 text-slate-800 ${
                      index % 2 === 0 ? "bg-white" : "bg-slate-50/80"
                    }`}
                  >
                    <td className="whitespace-nowrap px-3 py-2.5 text-slate-600">
                      {formatDate(event.created_at)}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className="text-xs text-slate-600">{event.scope_type}</span>
                      <span className="ml-1 font-mono text-xs text-slate-800">
                        {event.scope_id.slice(0, 12)}
                        {event.scope_id.length > 12 ? "…" : ""}
                      </span>
                    </td>
                    <td className="px-3 py-2.5">{event.call_kind}</td>
                    <td className="px-3 py-2.5">
                      <span className="font-medium text-slate-900">{event.provider}</span>
                      <span className="ml-1 font-mono text-xs text-slate-600">{event.model}</span>
                    </td>
                    <td className="px-3 py-2.5 tabular-nums">
                      {formatTokens(event.total_tokens)}
                    </td>
                    <td className="px-3 py-2.5 tabular-nums">
                      {formatUsd(event.estimated_usd)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
