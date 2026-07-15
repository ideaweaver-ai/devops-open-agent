"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import axios from "axios";
import { AppShell } from "@/components/layout/AppShell";
import { RequireAuth } from "@/components/auth/RequireAuth";
import {
  usePerformanceDebugDetail,
  useStartPerformanceDebug,
} from "@/hooks/usePerformanceDebug";
import type { HostDebugResult } from "@/types/performance";

const MAX_HOSTS = 50;

function parseHostText(raw: string): string[] {
  const seen = new Set<string>();
  const hosts: string[] = [];
  for (const line of raw.split(/\r?\n|,/)) {
    const host = line.trim();
    if (!host || host.startsWith("#")) {
      continue;
    }
    if (seen.has(host)) {
      continue;
    }
    seen.add(host);
    hosts.push(host);
    if (hosts.length >= MAX_HOSTS) {
      break;
    }
  }
  return hosts;
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (typeof item?.msg === "string" ? item.msg : JSON.stringify(item)))
        .join("; ");
    }
    return `Request failed with status ${error.response?.status ?? "unknown"}.`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "An unexpected error occurred.";
}

function severityClass(severity?: string | null): string {
  switch ((severity || "").toLowerCase()) {
    case "critical":
      return "border-red-300 bg-red-50 text-red-800";
    case "high":
      return "border-orange-300 bg-orange-50 text-orange-800";
    case "medium":
      return "border-amber-300 bg-amber-50 text-amber-900";
    case "low":
      return "border-emerald-300 bg-emerald-50 text-emerald-800";
    default:
      return "border-slate-200 bg-slate-50 text-slate-700";
  }
}

function statusLabel(status: HostDebugResult["status"]): string {
  switch (status) {
    case "pending":
      return "Pending";
    case "collecting":
      return "Collecting metrics";
    case "analyzing":
      return "Analyzing";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    default:
      return status;
  }
}

export function PerformanceDebuggingPage() {
  const searchParams = useSearchParams();
  const [hostText, setHostText] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [activeDebugId, setActiveDebugId] = useState<string | null>(null);
  const [userError, setUserError] = useState<string | null>(null);
  const [expandedHost, setExpandedHost] = useState<string | null>(null);

  const isViewOnly = Boolean(searchParams.get("debug_id"));

  useEffect(() => {
    const urlDebugId = searchParams.get("debug_id");
    if (urlDebugId && !activeDebugId) {
      setActiveDebugId(urlDebugId);
    }
  }, [searchParams, activeDebugId]);

  const startDebug = useStartPerformanceDebug();
  const detailQuery = usePerformanceDebugDetail(activeDebugId, Boolean(activeDebugId));

  const parsedHosts = useMemo(() => parseHostText(hostText), [hostText]);
  const isRunning =
    startDebug.isPending ||
    (detailQuery.data?.status !== "completed" &&
      detailQuery.data?.status !== "failed" &&
      Boolean(activeDebugId));

  const handleFileUpload = async (file: File | null) => {
    setUserError(null);
    if (!file) {
      return;
    }
    const lower = file.name.toLowerCase();
    if (!lower.endsWith(".txt") && !lower.endsWith(".csv")) {
      setUserError("Upload a .txt or .csv file with one hostname per line.");
      return;
    }
    try {
      const text = await file.text();
      const hosts = parseHostText(text);
      if (hosts.length === 0) {
        setUserError("No valid hostnames found in the uploaded file.");
        return;
      }
      setHostText(hosts.join("\n"));
      setFileName(file.name);
    } catch {
      setUserError("Could not read the uploaded file.");
    }
  };

  const handleStart = async () => {
    setUserError(null);
    const hosts = parseHostText(hostText);
    if (hosts.length === 0) {
      setUserError("Enter at least one hostname (or user@host), or upload a host list file.");
      return;
    }

    try {
      const response = await startDebug.mutateAsync({ hosts });
      setActiveDebugId(response.debug_id);
      setExpandedHost(null);
    } catch (error) {
      setUserError(getErrorMessage(error));
    }
  };

  const detail = detailQuery.data;

  return (
    <RequireAuth>
      <AppShell>
        <div className="space-y-6">
          {isViewOnly ? (
            <section>
              <Link
                href="/performance/investigations"
                className="inline-flex items-center gap-1 text-sm font-medium text-brand-600 hover:text-brand-700"
              >
                ← Back to Investigations
              </Link>
              <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900">
                Investigation Detail
              </h1>
            </section>
          ) : (
            <>
              <section>
                <h1 className="text-3xl font-bold tracking-tight text-slate-900">
                  Performance Debugging
                </h1>
                <p className="mt-2 text-slate-600">
                  Collect Linux CPU, memory, disk, and network signals over SSH, then run shared AI
                  analysis.
                </p>
              </section>

              <section className="panel-accent p-6">
                <div className="mb-5 border-b border-slate-200 pb-4">
                  <h2 className="panel-title">Start Debugging</h2>
                  <p className="mt-1 text-xs text-slate-600">
                    Provide one hostname, multiple hosts (one per line), or upload a host list file.
                  </p>
                </div>

                <div className="mb-5">
                  <label htmlFor="performance-hosts" className="section-label">
                    Hostnames
                  </label>
                  <textarea
                    id="performance-hosts"
                    value={hostText}
                    onChange={(event) => {
                      setHostText(event.target.value);
                      setFileName(null);
                    }}
                    disabled={isRunning}
                    rows={6}
                    placeholder={"web-01.example.com\nubuntu@db-02.example.com\n# comments are ignored"}
                    className="input-field mt-1 resize-y font-mono text-xs"
                  />
                  <p className="mt-2 text-xs text-slate-600">
                    {parsedHosts.length} host{parsedHosts.length === 1 ? "" : "s"} ready
                    {parsedHosts.length >= MAX_HOSTS ? ` (capped at ${MAX_HOSTS})` : ""}.
                    {fileName ? ` Loaded from ${fileName}.` : ""}
                  </p>
                </div>

                <div className="mb-5">
                  <p className="section-label">Or upload host list</p>
                  <input
                    type="file"
                    accept=".txt,.csv,text/plain,text/csv"
                    disabled={isRunning}
                    onChange={(event) => {
                      void handleFileUpload(event.target.files?.[0] ?? null);
                      event.target.value = "";
                    }}
                    className="mt-1 block w-full text-sm text-slate-700 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-brand-700 hover:file:bg-brand-100"
                  />
                  <p className="mt-2 text-xs text-slate-600">
                    Accepts .txt or .csv with one hostname (or user@host) per line.
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
                  disabled={isRunning || parsedHosts.length === 0}
                  className="btn-primary max-w-xs"
                >
                  {isRunning ? (
                    <span className="flex items-center gap-2">
                      <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                      Debugging...
                    </span>
                  ) : (
                    "Start Debugging"
                  )}
                </button>
              </section>
            </>
          )}

          {activeDebugId && (
            <section className="panel p-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="panel-title text-lg">Debug Progress</h2>
                  <p className="mt-1 text-xs font-mono text-slate-600">{activeDebugId}</p>
                </div>
                {detail && (
                  <div className="text-right text-sm text-slate-700">
                    <p className="font-semibold capitalize">{detail.status}</p>
                    <p className="text-xs text-slate-600">
                      {detail.progress_percentage}%
                      {detail.current_step ? ` · ${detail.current_step.replaceAll("_", " ")}` : ""}
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
                <p className="mt-4 text-sm text-red-700">{getErrorMessage(detailQuery.error)}</p>
              )}

              {detail?.error && (
                <p className="mt-4 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
                  {detail.error}
                </p>
              )}

              {detail?.overall_summary && (
                <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Overall summary
                  </p>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
                    {detail.overall_summary}
                  </p>
                </div>
              )}

              <div className="mt-5 space-y-3">
                {(detail?.hosts || []).map((host) => {
                  const open = expandedHost === host.host;
                  return (
                    <div
                      key={host.host}
                      className="rounded-xl border border-slate-200 bg-white"
                    >
                      <button
                        type="button"
                        className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left"
                        onClick={() => setExpandedHost(open ? null : host.host)}
                      >
                        <div className="min-w-0">
                          <p className="truncate font-mono text-sm font-semibold text-slate-900">
                            {host.host}
                          </p>
                          <p className="mt-1 text-xs text-slate-600">
                            {statusLabel(host.status)}
                            {host.message ? ` · ${host.message}` : ""}
                          </p>
                          {host.summary && (
                            <p className="mt-1 text-sm text-slate-700">{host.summary}</p>
                          )}
                          {host.error && (
                            <p className="mt-1 text-sm font-medium text-red-700">{host.error}</p>
                          )}
                        </div>
                        <div className="flex shrink-0 flex-col items-end gap-2">
                          {host.severity && (
                            <span
                              className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${severityClass(host.severity)}`}
                            >
                              {host.severity}
                            </span>
                          )}
                          <span className="text-xs text-slate-500">{open ? "Hide" : "Details"}</span>
                        </div>
                      </button>

                      {open && (
                        <div className="space-y-4 border-t border-slate-200 px-4 py-4">
                          {host.analysis && (
                            <div>
                              <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                                AI analysis
                              </p>
                              <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-800">
                                {host.analysis}
                              </pre>
                            </div>
                          )}
                          {host.evidence && (
                            <div>
                              <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                                Collected evidence
                              </p>
                              <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-900 p-3 font-mono text-[11px] leading-relaxed text-emerald-300">
                                {host.evidence}
                              </pre>
                            </div>
                          )}
                          {!host.analysis && !host.evidence && !host.error && (
                            <p className="text-sm text-slate-600">Waiting for results…</p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {!isViewOnly && (
            <aside className="rounded-xl border border-amber-300 bg-amber-50 px-5 py-4 text-sm text-amber-950">
              <p className="font-semibold">NOTE</p>
              <p className="mt-1.5 leading-relaxed">
                Before starting Performance Debugging, set up <strong>passwordless SSH</strong> from
                the machine (or Docker host) running DevOps Open Agent to every target hostname.
                The agent uses OpenSSH <code className="rounded bg-amber-100 px-1">BatchMode</code>{" "}
                only — there is no password prompt or key upload in the UI. Use{" "}
                <code className="rounded bg-amber-100 px-1">hostname</code> or{" "}
                <code className="rounded bg-amber-100 px-1">user@host</code>. Docker Compose mounts{" "}
                <code className="rounded bg-amber-100 px-1">~/.ssh</code> into the backend container
                read-only.
              </p>
            </aside>
          )}
        </div>
      </AppShell>
    </RequireAuth>
  );
}

export default PerformanceDebuggingPage;
