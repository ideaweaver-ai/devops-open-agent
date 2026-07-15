"use client";

import { useMemo, useState } from "react";
import axios from "axios";
import { AppShell } from "@/components/layout/AppShell";
import { RequireAuth } from "@/components/auth/RequireAuth";
import {
  useSecurityScanDetail,
  useStartSecurityScan,
} from "@/hooks/useSecurityScan";
import { useClusters, resolveClusterOptions, resolveDefaultCluster } from "@/hooks/useClusters";
import { ClusterSelector } from "@/components/ClusterSelector";
import type {
  ScanType,
  VulnerabilityFinding,
  MisconfigFinding,
} from "@/types/security";

const ALL_SEVERITIES = ["UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"];
const DEFAULT_SEVERITIES = ["UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"];

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail))
      return detail
        .map((item) =>
          typeof item?.msg === "string" ? item.msg : JSON.stringify(item),
        )
        .join("; ");
    return `Request failed with status ${error.response?.status ?? "unknown"}.`;
  }
  if (error instanceof Error) return error.message;
  return "An unexpected error occurred.";
}

function severityBadge(severity: string): string {
  switch (severity.toUpperCase()) {
    case "CRITICAL":
      return "border-red-300 bg-red-50 text-red-800";
    case "HIGH":
      return "border-orange-300 bg-orange-50 text-orange-800";
    case "MEDIUM":
      return "border-amber-300 bg-amber-50 text-amber-900";
    case "LOW":
      return "border-emerald-300 bg-emerald-50 text-emerald-800";
    default:
      return "border-slate-200 bg-slate-50 text-slate-700";
  }
}

function SeverityCard({
  label,
  count,
  color,
}: {
  label: string;
  count: number;
  color: string;
}) {
  return (
    <div
      className={`flex flex-col items-center rounded-xl border px-5 py-3 ${color}`}
    >
      <span className="text-2xl font-bold">{count}</span>
      <span className="text-xs font-semibold uppercase tracking-wide">
        {label}
      </span>
    </div>
  );
}

export function SecurityScanningPage() {
  const [scanType, setScanType] = useState<ScanType>("image");
  const [imageName, setImageName] = useState("");
  const [namespace, setNamespace] = useState("");
  const [includeAi, setIncludeAi] = useState(true);
  const [severityFilter, setSeverityFilter] =
    useState<string[]>(DEFAULT_SEVERITIES);
  const [activeScanId, setActiveScanId] = useState<string | null>(null);
  const [userError, setUserError] = useState<string | null>(null);
  const [showAiPanel, setShowAiPanel] = useState(true);
  const [sortField, setSortField] = useState<"severity" | "id">("severity");
  const [sortAsc, setSortAsc] = useState(false);

  const clustersQuery = useClusters();
  const clusterOptions = resolveClusterOptions(clustersQuery.data?.clusters);
  const defaultCluster = resolveDefaultCluster(clustersQuery.data?.clusters);
  const [selectedCluster, setSelectedCluster] = useState<string>("");

  const activeCluster = selectedCluster || defaultCluster;

  const startScan = useStartSecurityScan();
  const detailQuery = useSecurityScanDetail(activeScanId, Boolean(activeScanId));

  const isRunning =
    startScan.isPending ||
    (detailQuery.data?.status !== "completed" &&
      detailQuery.data?.status !== "failed" &&
      Boolean(activeScanId));

  const handleSeverityToggle = (sev: string) => {
    setSeverityFilter((prev) =>
      prev.includes(sev) ? prev.filter((s) => s !== sev) : [...prev, sev],
    );
  };

  const handleStart = async () => {
    setUserError(null);
    if (scanType === "image" && !imageName.trim()) {
      setUserError("Enter a container image name (e.g. nginx:latest).");
      return;
    }
    if (severityFilter.length === 0) {
      setUserError("Select at least one severity level.");
      return;
    }
    try {
      const response = await startScan.mutateAsync({
        scan_type: scanType,
        image_name: scanType === "image" ? imageName.trim() : undefined,
        namespace: scanType === "kubernetes" && namespace.trim() ? namespace.trim() : undefined,
        context: scanType === "kubernetes" ? activeCluster : undefined,
        include_ai: includeAi,
        severity_filter: severityFilter,
      });
      setActiveScanId(response.scan_id);
    } catch (error) {
      setUserError(getErrorMessage(error));
    }
  };

  const detail = detailQuery.data;
  const result = detail?.result;

  const severityOrder: Record<string, number> = {
    CRITICAL: 0,
    HIGH: 1,
    MEDIUM: 2,
    LOW: 3,
    UNKNOWN: 4,
  };

  const sortedVulns = useMemo(() => {
    if (!result?.vulnerabilities) return [];
    const items = [...result.vulnerabilities];
    items.sort((a, b) => {
      if (sortField === "severity") {
        const diff =
          (severityOrder[a.severity] ?? 5) - (severityOrder[b.severity] ?? 5);
        return sortAsc ? -diff : diff;
      }
      const cmp = a.vulnerability_id.localeCompare(b.vulnerability_id);
      return sortAsc ? cmp : -cmp;
    });
    return items;
  }, [result?.vulnerabilities, sortField, sortAsc]);

  const sortedMisconfigs = useMemo(() => {
    if (!result?.misconfigurations) return [];
    const items = [...result.misconfigurations];
    items.sort((a, b) => {
      if (sortField === "severity") {
        const diff =
          (severityOrder[a.severity] ?? 5) - (severityOrder[b.severity] ?? 5);
        return sortAsc ? -diff : diff;
      }
      const cmp = a.id.localeCompare(b.id);
      return sortAsc ? cmp : -cmp;
    });
    return items;
  }, [result?.misconfigurations, sortField, sortAsc]);

  const handleSort = (field: "severity" | "id") => {
    if (sortField === field) {
      setSortAsc((prev) => !prev);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  return (
    <RequireAuth>
      <AppShell>
        <div className="space-y-6">
          <section>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">
              Security Scanning
            </h1>
            <p className="mt-2 text-slate-600">
              Scan container images and Kubernetes clusters for vulnerabilities
              and misconfigurations using Trivy, with optional AI analysis.
            </p>
          </section>

          {/* Scan Form */}
          <section className="panel-accent p-6">
            <div className="mb-5 border-b border-slate-200 pb-4">
              <h2 className="panel-title">Start Scan</h2>
              <p className="mt-1 text-xs text-slate-600">
                Choose a scan type and configure options.
              </p>
            </div>

            {/* Scan Type Tabs */}
            <div className="mb-5 flex gap-2">
              <button
                type="button"
                onClick={() => setScanType("image")}
                disabled={isRunning}
                className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
                  scanType === "image"
                    ? "bg-brand-600 text-white shadow-sm"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
              >
                Container Image
              </button>
              <button
                type="button"
                onClick={() => setScanType("kubernetes")}
                disabled={isRunning}
                className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
                  scanType === "kubernetes"
                    ? "bg-brand-600 text-white shadow-sm"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
              >
                Kubernetes Cluster
              </button>
            </div>

            {/* Image Name */}
            {scanType === "image" && (
              <div className="mb-5">
                <label htmlFor="image-name" className="section-label">
                  Image Name
                </label>
                <input
                  id="image-name"
                  type="text"
                  value={imageName}
                  onChange={(e) => setImageName(e.target.value)}
                  disabled={isRunning}
                  placeholder="nginx:latest, myregistry.io/app:v1"
                  className="input-field mt-1"
                />
              </div>
            )}

            {/* Cluster + Namespace */}
            {scanType === "kubernetes" && (
              <>
                <div className="mb-5">
                  <ClusterSelector
                    clusters={
                      clustersQuery.data?.clusters?.map((c) => ({
                        cluster_id: c.cluster_id,
                        context: c.cluster_id,
                        name: c.cluster_id,
                        active: c.active,
                      })) ?? []
                    }
                    clusterId={activeCluster}
                    onClusterChange={setSelectedCluster}
                    disabled={isRunning}
                    loading={clustersQuery.isLoading}
                    error={
                      clustersQuery.isError
                        ? "Could not load clusters from kubeconfig."
                        : null
                    }
                    label="Cluster"
                    compact
                  />
                </div>
                <div className="mb-5">
                  <label htmlFor="k8s-namespace" className="section-label">
                    Namespace (optional)
                  </label>
                  <input
                    id="k8s-namespace"
                    type="text"
                    value={namespace}
                    onChange={(e) => setNamespace(e.target.value)}
                    disabled={isRunning}
                    placeholder="Leave blank to scan all namespaces"
                    className="input-field mt-1"
                  />
                </div>
              </>
            )}

            {/* Severity Filter */}
            <div className="mb-5">
              <p className="section-label">Severity Filter</p>
              <div className="mt-2 flex flex-wrap gap-3">
                {ALL_SEVERITIES.map((sev) => (
                  <label
                    key={sev}
                    className="flex items-center gap-1.5 text-sm text-slate-700"
                  >
                    <input
                      type="checkbox"
                      checked={severityFilter.includes(sev)}
                      onChange={() => handleSeverityToggle(sev)}
                      disabled={isRunning}
                      className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                    />
                    {sev}
                  </label>
                ))}
              </div>
            </div>

            {/* AI Toggle */}
            <div className="mb-5">
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={includeAi}
                  onChange={(e) => setIncludeAi(e.target.checked)}
                  disabled={isRunning}
                  className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                />
                Include AI Analysis
              </label>
              <p className="ml-6 mt-1 text-xs text-slate-500">
                Uses the configured LLM to prioritize findings and suggest
                remediations.
              </p>
            </div>

            {userError && (
              <div className="mb-4 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
                {userError}
              </div>
            )}

            <button
              type="button"
              onClick={() => void handleStart()}
              disabled={
                isRunning ||
                (scanType === "image" && !imageName.trim()) ||
                severityFilter.length === 0
              }
              className="btn-primary max-w-xs"
            >
              {isRunning ? (
                <span className="flex items-center gap-2">
                  <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Scanning...
                </span>
              ) : scanType === "image" ? (
                "Scan Image"
              ) : (
                "Scan Cluster"
              )}
            </button>
          </section>

          {/* Progress / Results */}
          {activeScanId && (
            <section className="panel p-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="panel-title text-lg">Scan Progress</h2>
                  <p className="mt-1 font-mono text-xs text-slate-600">
                    {activeScanId}
                  </p>
                </div>
                {detail && (
                  <div className="text-right text-sm text-slate-700">
                    <p className="font-semibold capitalize">{detail.status}</p>
                    <p className="text-xs text-slate-600">
                      {detail.progress_percentage}%
                      {detail.current_step
                        ? ` · ${detail.current_step.replaceAll("_", " ")}`
                        : ""}
                    </p>
                  </div>
                )}
              </div>

              {detail && (
                <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-brand-600 transition-all"
                    style={{ width: `${detail.progress_percentage}%` }}
                  />
                </div>
              )}

              {detailQuery.isError && (
                <p className="mt-4 text-sm text-red-700">
                  {getErrorMessage(detailQuery.error)}
                </p>
              )}

              {detail?.error && (
                <p className="mt-4 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
                  {detail.error}
                </p>
              )}

              {/* Summary Cards */}
              {result && (
                <div className="mt-5 flex flex-wrap gap-3">
                  <SeverityCard
                    label="Critical"
                    count={result.summary["CRITICAL"] || 0}
                    color="border-red-300 bg-red-50 text-red-800"
                  />
                  <SeverityCard
                    label="High"
                    count={result.summary["HIGH"] || 0}
                    color="border-orange-300 bg-orange-50 text-orange-800"
                  />
                  <SeverityCard
                    label="Medium"
                    count={result.summary["MEDIUM"] || 0}
                    color="border-amber-300 bg-amber-50 text-amber-900"
                  />
                  <SeverityCard
                    label="Low"
                    count={result.summary["LOW"] || 0}
                    color="border-emerald-300 bg-emerald-50 text-emerald-800"
                  />
                  {(result.summary["UNKNOWN"] || 0) > 0 && (
                    <SeverityCard
                      label="Unknown"
                      count={result.summary["UNKNOWN"] || 0}
                      color="border-slate-200 bg-slate-50 text-slate-700"
                    />
                  )}
                </div>
              )}

              {/* Vulnerabilities Table */}
              {sortedVulns.length > 0 && (
                <div className="mt-6">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
                    Vulnerabilities ({sortedVulns.length})
                  </h3>
                  <div className="mt-3 overflow-x-auto rounded-xl border border-slate-200">
                    <table className="w-full text-left text-sm">
                      <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
                        <tr>
                          <th
                            className="cursor-pointer px-4 py-3"
                            onClick={() => handleSort("severity")}
                          >
                            Severity{" "}
                            {sortField === "severity"
                              ? sortAsc
                                ? "↑"
                                : "↓"
                              : ""}
                          </th>
                          <th
                            className="cursor-pointer px-4 py-3"
                            onClick={() => handleSort("id")}
                          >
                            ID{" "}
                            {sortField === "id"
                              ? sortAsc
                                ? "↑"
                                : "↓"
                              : ""}
                          </th>
                          <th className="px-4 py-3">Package</th>
                          <th className="px-4 py-3">Installed</th>
                          <th className="px-4 py-3">Fixed</th>
                          <th className="px-4 py-3">Title</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {sortedVulns.map(
                          (v: VulnerabilityFinding, i: number) => (
                            <tr key={`${v.vulnerability_id}-${i}`} className="hover:bg-slate-50">
                              <td className="px-4 py-2.5">
                                <span
                                  className={`inline-block rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${severityBadge(v.severity)}`}
                                >
                                  {v.severity}
                                </span>
                              </td>
                              <td className="px-4 py-2.5 font-mono text-xs">
                                {v.vulnerability_id}
                              </td>
                              <td className="px-4 py-2.5 font-mono text-xs">
                                {v.pkg_name}
                              </td>
                              <td className="px-4 py-2.5 font-mono text-xs">
                                {v.installed_version}
                              </td>
                              <td className="px-4 py-2.5 font-mono text-xs">
                                {v.fixed_version || (
                                  <span className="text-slate-400">—</span>
                                )}
                              </td>
                              <td className="max-w-xs truncate px-4 py-2.5 text-xs text-slate-700">
                                {v.title}
                              </td>
                            </tr>
                          ),
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Misconfigurations Table */}
              {sortedMisconfigs.length > 0 && (
                <div className="mt-6">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
                    Misconfigurations ({sortedMisconfigs.length})
                  </h3>
                  <div className="mt-3 overflow-x-auto rounded-xl border border-slate-200">
                    <table className="w-full text-left text-sm">
                      <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
                        <tr>
                          <th className="px-4 py-3">Severity</th>
                          <th className="px-4 py-3">ID</th>
                          <th className="px-4 py-3">Resource</th>
                          <th className="px-4 py-3">Title</th>
                          <th className="px-4 py-3">Resolution</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {sortedMisconfigs.map(
                          (m: MisconfigFinding, i: number) => (
                            <tr key={`${m.id}-${i}`} className="hover:bg-slate-50">
                              <td className="px-4 py-2.5">
                                <span
                                  className={`inline-block rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${severityBadge(m.severity)}`}
                                >
                                  {m.severity}
                                </span>
                              </td>
                              <td className="px-4 py-2.5 font-mono text-xs">
                                {m.id}
                              </td>
                              <td className="max-w-[10rem] truncate px-4 py-2.5 font-mono text-xs">
                                {m.resource || (
                                  <span className="text-slate-400">—</span>
                                )}
                              </td>
                              <td className="max-w-xs truncate px-4 py-2.5 text-xs text-slate-700">
                                {m.title}
                              </td>
                              <td className="max-w-xs truncate px-4 py-2.5 text-xs text-slate-600">
                                {m.resolution}
                              </td>
                            </tr>
                          ),
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* AI Analysis Panel */}
              {result?.ai_analysis && (
                <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50">
                  <button
                    type="button"
                    onClick={() => setShowAiPanel((p) => !p)}
                    className="flex w-full items-center justify-between px-5 py-4 text-left"
                  >
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
                        AI Analysis
                      </h3>
                      {result.llm_provider && (
                        <span className="rounded-full border border-brand-200 bg-brand-50 px-2 py-0.5 text-[10px] font-semibold uppercase text-brand-700">
                          {result.llm_provider}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-slate-500">
                      {showAiPanel ? "Collapse" : "Expand"}
                    </span>
                  </button>
                  {showAiPanel && (
                    <div className="border-t border-slate-200 px-5 py-4">
                      <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
                        {result.ai_analysis}
                      </pre>
                    </div>
                  )}
                </div>
              )}

              {result?.llm_error && (
                <div className="mt-4 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  <p className="font-semibold">AI Analysis Error</p>
                  <p className="mt-1">{result.llm_error}</p>
                </div>
              )}

              {/* Empty state when scan complete but no findings */}
              {result &&
                sortedVulns.length === 0 &&
                sortedMisconfigs.length === 0 &&
                detail?.status === "completed" && (
                  <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-center">
                    <p className="text-lg font-semibold text-emerald-800">
                      No vulnerabilities or misconfigurations found
                    </p>
                    <p className="mt-1 text-sm text-emerald-700">
                      The scan completed successfully with no findings matching
                      your severity filter.
                    </p>
                  </div>
                )}
            </section>
          )}

          <aside className="rounded-xl border border-blue-200 bg-blue-50 px-5 py-4 text-sm text-blue-950">
            <p className="font-semibold">NOTE</p>
            <p className="mt-1.5 leading-relaxed">
              Security scanning is powered by{" "}
              <a
                href="https://github.com/aquasecurity/trivy"
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold underline hover:text-blue-700"
              >
                Trivy
              </a>{" "}
              (bundled in the Docker image). Container image scans pull the
              image inside the backend container. Kubernetes cluster scans
              require a valid kubeconfig mounted into the container (same as the
              Kubernetes Debugging agent).
            </p>
          </aside>
        </div>
      </AppShell>
    </RequireAuth>
  );
}

export default SecurityScanningPage;
