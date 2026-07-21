"use client";

import type { ObservabilityFinding, ObservabilityResult } from "@/types/observability";

interface ObservabilityEvidencePanelProps {
  data?: ObservabilityResult | Record<string, unknown> | null;
  className?: string;
}

function asObservability(data: ObservabilityEvidencePanelProps["data"]): ObservabilityResult | null {
  if (!data || typeof data !== "object") return null;
  const record = data as ObservabilityResult;
  if (!("findings" in record) && !("enabled" in record) && !("summary" in record)) {
    return null;
  }
  return {
    enabled: Boolean(record.enabled),
    prometheus: record.prometheus ?? { enabled: false },
    grafana: record.grafana ?? { enabled: false },
    loki: record.loki ?? { enabled: false },
    opentelemetry: record.opentelemetry ?? { enabled: false },
    findings: Array.isArray(record.findings) ? record.findings : [],
    summary: record.summary ?? null,
  };
}

function severityClass(severity?: string | null): string {
  const value = (severity || "").toLowerCase();
  if (value === "high" || value === "critical") {
    return "border-rose-500/20 bg-rose-500/10 text-rose-200";
  }
  if (value === "medium") {
    return "border-amber-500/20 bg-amber-500/10 text-amber-200";
  }
  return "border-slate-500/20 bg-slate-500/10 text-slate-300";
}

function StatusChip({
  label,
  enabled,
  error,
}: {
  label: string;
  enabled?: boolean;
  error?: string | null;
}) {
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
        error
          ? "border-rose-500/20 bg-rose-500/10 text-rose-200"
          : enabled
            ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-200"
            : "border-white/10 bg-slate-900/60 text-slate-500"
      }`}
      title={error || undefined}
    >
      {label}
      {error ? " error" : enabled ? " on" : " off"}
    </span>
  );
}

export function ObservabilityEvidencePanel({
  data,
  className = "",
}: ObservabilityEvidencePanelProps) {
  const observability = asObservability(data);
  if (!observability) return null;

  const findings = observability.findings as ObservabilityFinding[];
  const hasSignal =
    observability.enabled || findings.length > 0 || Boolean(observability.summary);

  if (!hasSignal) return null;

  return (
    <section className={`panel rounded-2xl p-5 sm:p-6 ${className}`.trim()}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-white">Observability evidence</h3>
          <p className="mt-1 text-xs text-slate-400">
            {observability.summary ||
              "Prometheus and Grafana signals collected for this investigation."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusChip
            label="Prometheus"
            enabled={observability.prometheus?.enabled}
            error={observability.prometheus?.error}
          />
          <StatusChip
            label="Grafana"
            enabled={observability.grafana?.enabled}
            error={observability.grafana?.error}
          />
        </div>
      </div>

      {findings.length === 0 ? (
        <p className="text-sm text-slate-500">
          Integrations are configured, but no matching metric/dashboard findings were returned.
        </p>
      ) : (
        <ul className="space-y-3">
          {findings.map((finding, index) => (
            <li
              key={`${finding.source}-${finding.title}-${index}`}
              className="rounded-xl border border-white/[0.06] bg-slate-950/50 px-4 py-3"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-brand-500/20 bg-brand-500/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-brand-200">
                  {finding.source}
                </span>
                {finding.severity ? (
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${severityClass(
                      finding.severity,
                    )}`}
                  >
                    {finding.severity}
                  </span>
                ) : null}
                <span className="text-sm font-medium text-slate-100">{finding.title}</span>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-slate-300">{finding.detail}</p>
              {finding.query ? (
                <p className="mt-2 font-mono text-[11px] text-slate-500">{finding.query}</p>
              ) : null}
              {finding.timestamp ? (
                <p className="mt-1 text-[11px] text-slate-500">{finding.timestamp}</p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
