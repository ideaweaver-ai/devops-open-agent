"use client";

import Link from "next/link";
import type { AwsAccountSummary, AwsIssueType, AwsRegionInfo, CloudWatchWindow } from "@/types/aws";
import { AwsAccountSelector } from "@/components/aws/AwsAccountSelector";
import { AWS_ISSUE_TYPES } from "@/lib/awsIssueTypes";

const CLOUDWATCH_WINDOWS: { value: CloudWatchWindow; label: string }[] = [
  { value: "1h", label: "Last 1 hour" },
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
];

const SUPPORTED_AWS_SERVICES = [
  "EC2",
  "Lambda",
  "S3",
  "VPC",
  "Security Groups",
  "Load Balancers",
  "Auto Scaling",
  "CloudWatch",
  "CloudTrail",
  "Prometheus",
  "Grafana",
] as const;

interface AwsInvestigationFormProps {
  accounts: AwsAccountSummary[];
  accountId: string;
  onAccountChange: (accountId: string) => void;
  regions: AwsRegionInfo[];
  region: string;
  onRegionChange: (region: string) => void;
  issueType: AwsIssueType;
  onIssueTypeChange: (issueType: AwsIssueType) => void;
  query: string;
  onQueryChange: (query: string) => void;
  cloudwatchWindow: CloudWatchWindow;
  onCloudwatchWindowChange: (window: CloudWatchWindow) => void;
  onInvestigate: () => void;
  isLoading: boolean;
  disabled?: boolean;
  accountsLoading?: boolean;
  accountsError?: string | null;
  regionsLoading?: boolean;
  regionsError?: string | null;
  includeRag?: boolean;
  onIncludeRagChange?: (value: boolean) => void;
  ragAvailable?: boolean;
  prometheusEnabled?: boolean;
  grafanaEnabled?: boolean;
  observabilityLoading?: boolean;
}

export function AwsInvestigationForm({
  accounts,
  accountId,
  onAccountChange,
  regions,
  region,
  onRegionChange,
  issueType,
  onIssueTypeChange,
  query,
  onQueryChange,
  cloudwatchWindow,
  onCloudwatchWindowChange,
  onInvestigate,
  isLoading,
  disabled = false,
  accountsLoading = false,
  accountsError = null,
  regionsLoading = false,
  regionsError = null,
  includeRag = false,
  onIncludeRagChange,
  ragAvailable = false,
  prometheusEnabled = false,
  grafanaEnabled = false,
  observabilityLoading = false,
}: AwsInvestigationFormProps) {
  const observabilityReady = prometheusEnabled || grafanaEnabled;

  return (
    <div className="panel-accent p-6">
      <div className="mb-5 flex items-center gap-3 border-b border-slate-200 pb-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-orange-200 bg-orange-50">
          <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4 text-orange-700" aria-hidden>
            <path
              d="M12 2L4 6v6c0 5 3.5 9.5 8 11 4.5-1.5 8-6 8-11V6l-8-4z"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <div>
          <h2 className="panel-title">Troubleshoot AWS Infrastructure</h2>
          <p className="text-xs text-slate-600">
            Discover EC2, Lambda, S3, networking, and load balancers — enrich with
            Prometheus/Grafana metrics — then run AI analysis
          </p>
        </div>
      </div>

      <div className="mb-5">
        <p className="section-label">Supported Services</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {SUPPORTED_AWS_SERVICES.map((service) => (
            <span
              key={service}
              className="rounded-full border border-orange-200 bg-orange-50 px-3 py-1 text-[11px] font-semibold text-orange-800"
            >
              {service}
            </span>
          ))}
        </div>
      </div>

      <div
        className={`mb-5 rounded-xl border px-4 py-3 ${
          observabilityReady
            ? "border-emerald-200 bg-emerald-50"
            : "border-slate-200 bg-slate-50"
        }`}
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-slate-900">
              Observability evidence (Prometheus / Grafana)
            </p>
            <p className="mt-1 text-xs text-slate-600">
              {observabilityLoading
                ? "Checking integration status..."
                : observabilityReady
                  ? "Enabled integrations are collected automatically during each AWS investigation (host CPU, load, memory, dashboards). Findings appear under the Observability results tab."
                  : "Not configured yet. Connect Prometheus and/or Grafana so investigations can include live metrics (for example EC2 CPU stress from Alloy)."}
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <span
                className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                  prometheusEnabled
                    ? "border-emerald-300 bg-emerald-100 text-emerald-800"
                    : "border-slate-300 bg-white text-slate-500"
                }`}
              >
                Prometheus {prometheusEnabled ? "on" : "off"}
              </span>
              <span
                className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                  grafanaEnabled
                    ? "border-emerald-300 bg-emerald-100 text-emerald-800"
                    : "border-slate-300 bg-white text-slate-500"
                }`}
              >
                Grafana {grafanaEnabled ? "on" : "off"}
              </span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/integrations/prometheus"
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
            >
              Configure Prometheus
            </Link>
            <Link
              href="/integrations/grafana"
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
            >
              Configure Grafana
            </Link>
          </div>
        </div>
      </div>

      <div className="mb-5">
        <AwsAccountSelector
          accounts={accounts}
          accountId={accountId}
          onAccountChange={onAccountChange}
          disabled={disabled || isLoading}
          loading={accountsLoading}
          error={accountsError}
        />
      </div>

      {accountId && (
        <div className="mb-5">
          <p className="section-label">Select Region</p>
          {regionsLoading && regions.length === 0 ? (
            <div className="mt-3 flex items-center gap-2 text-xs text-slate-600">
              <span className="inline-flex h-3 w-3 animate-spin rounded-full border border-slate-300 border-t-orange-500" />
              Loading regions...
            </div>
          ) : (
            <div className="mt-3 flex flex-wrap gap-2">
              {regions.map((item) => {
                const selected = region === item.region;
                return (
                  <button
                    key={item.region}
                    type="button"
                    disabled={disabled || isLoading}
                    onClick={() => onRegionChange(item.region)}
                    className={`rounded-lg border px-3 py-1.5 font-mono text-xs font-medium transition ${
                      selected
                        ? "border-orange-500 bg-orange-50 text-orange-800 ring-1 ring-orange-500/30"
                        : "border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50"
                    } ${disabled || isLoading ? "cursor-not-allowed opacity-60" : ""}`}
                  >
                    {item.region}
                  </button>
                );
              })}
            </div>
          )}
          {regionsError && (
            <p className="mt-2.5 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-900">
              {regionsError}
            </p>
          )}
        </div>
      )}

      <div className="mb-5">
        <p className="section-label">What do you want to troubleshoot?</p>
        <div
          role="radiogroup"
          aria-label="Issue type"
          className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2"
        >
          {AWS_ISSUE_TYPES.map((item) => {
            const selected = issueType === item.value;
            return (
              <button
                key={item.value}
                type="button"
                role="radio"
                aria-checked={selected}
                disabled={disabled || isLoading}
                onClick={() => onIssueTypeChange(item.value)}
                className={`rounded-xl border px-4 py-3 text-left transition ${
                  selected
                    ? "border-orange-500 bg-orange-50 shadow-sm ring-1 ring-orange-500/30"
                    : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                } ${disabled || isLoading ? "cursor-not-allowed opacity-60" : "cursor-pointer"}`}
              >
                <p className="text-sm font-semibold text-slate-900">{item.label}</p>
                <p className="mt-1 text-xs leading-relaxed text-slate-600">{item.description}</p>
              </button>
            );
          })}
        </div>
      </div>

      <div className="mb-5">
        <label htmlFor="aws-issue-query" className="section-label">
          Describe the issue (optional)
        </label>
        <textarea
          id="aws-issue-query"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          disabled={disabled || isLoading}
          placeholder="e.g. I opened HTTP to the internet on a security group and want to know if it's exposed..."
          rows={3}
          className="input-field mt-3 resize-y"
        />
      </div>

      <div className="mb-5">
        <p className="section-label">Evidence Window</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {CLOUDWATCH_WINDOWS.map((item) => {
            const selected = cloudwatchWindow === item.value;
            return (
              <button
                key={item.value}
                type="button"
                disabled={disabled || isLoading}
                onClick={() => onCloudwatchWindowChange(item.value)}
                className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                  selected
                    ? "border-brand-500 bg-brand-50 text-brand-800 ring-1 ring-brand-500/30"
                    : "border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50"
                } ${disabled || isLoading ? "cursor-not-allowed opacity-60" : ""}`}
              >
                {item.label}
              </button>
            );
          })}
        </div>
        <p className="mt-2 text-xs text-slate-600">
          Applies to CloudWatch metrics and CloudTrail lookback
        </p>
      </div>

      {ragAvailable && (
        <label className="mb-5 flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
          <input
            type="checkbox"
            checked={includeRag}
            disabled={disabled || isLoading}
            onChange={(event) => onIncludeRagChange?.(event.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-slate-300 text-orange-600 focus:ring-orange-500"
          />
          <span>
            <span className="block text-sm font-medium text-slate-900">
              Include past investigations (RAG)
            </span>
            <span className="mt-0.5 block text-xs text-slate-600">
              Retrieve similar prior AWS investigations from Qdrant and factor them into the
              AI analysis.
            </span>
          </span>
        </label>
      )}

      <button
        type="button"
        onClick={onInvestigate}
        disabled={disabled || isLoading || !accountId || !region}
        className="btn-primary max-w-xs"
      >
        {isLoading ? (
          <span className="flex items-center gap-2">
            <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            Troubleshooting...
          </span>
        ) : (
          "Troubleshoot"
        )}
      </button>
    </div>
  );
}
