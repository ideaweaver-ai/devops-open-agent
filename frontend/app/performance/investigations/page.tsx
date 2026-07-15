"use client";

import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { usePerformanceDebugHistory } from "@/hooks/usePerformanceDebug";

function formatDate(value?: string | null) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function statusBadgeClass(status: string) {
  switch (status) {
    case "completed":
      return "border-emerald-500/20 bg-emerald-500/10 text-emerald-300";
    case "failed":
      return "border-red-500/20 bg-red-500/10 text-red-300";
    case "running":
      return "border-brand-500/20 bg-brand-500/10 text-brand-300";
    default:
      return "border-slate-500/20 bg-slate-500/10 text-slate-300";
  }
}

export default function PerformanceInvestigationsPage() {
  const { data, isLoading, isError } = usePerformanceDebugHistory();

  return (
    <RequireAuth>
      <AppShell>
        <div className="panel-accent p-6">
          <div className="mb-5 flex items-center justify-between gap-4 border-b border-white/[0.06] pb-4">
            <div>
              <p className="panel-subtitle mb-1">Investigations</p>
              <h2 className="panel-title">Performance Debug Runs</h2>
            </div>
            {!isLoading && !isError && (data?.jobs.length ?? 0) > 0 && (
              <span className="rounded-full border border-white/[0.08] bg-slate-800/60 px-3 py-1 text-xs font-medium tabular-nums text-slate-400">
                {data?.jobs.length} total
              </span>
            )}
          </div>

          {isLoading && (
            <div className="flex items-center gap-2.5 text-sm text-slate-400">
              <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-brand-400" />
              Loading investigations...
            </div>
          )}
          {isError && (
            <p className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              Unable to load investigations. Is the backend running?
            </p>
          )}

          {!isLoading && !isError && (data?.jobs.length ?? 0) === 0 && (
            <div className="rounded-xl border border-dashed border-white/[0.08] bg-slate-950/30 px-6 py-10 text-center">
              <p className="text-sm text-slate-400">
                No debug runs yet.{" "}
                <Link href="/performance" className="text-brand-400 hover:text-brand-300">
                  Run your first performance debug
                </Link>
                .
              </p>
            </div>
          )}

          {!isLoading && !isError && (data?.jobs.length ?? 0) > 0 && (
            <div className="overflow-x-auto rounded-xl border border-white/[0.05]">
              <table className="min-w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-white/[0.06] bg-slate-950/50">
                    <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                      Summary
                    </th>
                    <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                      Hosts
                    </th>
                    <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                      Status
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
                  {data?.jobs.map((item, index) => (
                    <tr
                      key={item.debug_id}
                      className={`border-b border-white/[0.04] text-slate-300 transition hover:bg-brand-500/5 ${
                        index % 2 === 0 ? "bg-transparent" : "bg-slate-950/20"
                      }`}
                    >
                      <td className="max-w-xs px-4 py-3.5">
                        <span className="line-clamp-2 leading-relaxed">
                          {item.overall_summary || "Debug run in progress / no summary"}
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className="inline-flex rounded-md border border-white/[0.08] bg-slate-800/50 px-2 py-0.5 font-mono text-xs text-slate-300">
                          {item.host_count} host{item.host_count !== 1 ? "s" : ""}
                        </span>
                        {item.hosts_summary && (
                          <span className="ml-2 text-xs text-slate-500">{item.hosts_summary}</span>
                        )}
                      </td>
                      <td className="px-4 py-3.5">
                        <span className={`status-pill border ${statusBadgeClass(item.status)}`}>
                          {item.status}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3.5 text-slate-400">
                        {formatDate(item.created_at)}
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <Link
                          href={`/performance?debug_id=${item.debug_id}`}
                          className="text-xs font-medium text-brand-400 hover:text-brand-300"
                        >
                          View →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </AppShell>
    </RequireAuth>
  );
}
