"use client";

import { useState } from "react";
import { useAuditEvents } from "@/hooks/useAuditEvents";

function formatDate(value: string): string {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function formatMetadata(metadata: Record<string, unknown> | null | undefined): string {
  if (!metadata || Object.keys(metadata).length === 0) {
    return "—";
  }
  try {
    return JSON.stringify(metadata);
  } catch {
    return "—";
  }
}

const ACTION_FILTERS = [
  { id: "", label: "All actions" },
  { id: "investigation.started", label: "Investigation started" },
  { id: "investigation.rerun", label: "Investigation re-run" },
  { id: "integration.updated", label: "Integration updated" },
  { id: "pricing.updated", label: "Pricing updated" },
  { id: "budget.updated", label: "Budget updated" },
] as const;

export function AuditLogPage() {
  const [action, setAction] = useState("");
  const query = useAuditEvents({
    action: action || undefined,
    limit: 150,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Audit log</h1>
          <p className="mt-1 text-sm text-slate-600">
            Your investigation runs and integration setting changes.
          </p>
        </div>
        <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Filter
          <select
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-800"
            value={action}
            onChange={(event) => setAction(event.target.value)}
          >
            {ACTION_FILTERS.map((item) => (
              <option key={item.id || "all"} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {query.isLoading && (
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-6 text-sm text-slate-600">
          Loading audit events…
        </div>
      )}

      {query.isError && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          Failed to load audit events.
        </div>
      )}

      {query.data && (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Actor</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Resource</th>
                  <th className="px-4 py-3">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {query.data.events.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                      No audit events yet.
                    </td>
                  </tr>
                )}
                {query.data.events.map((event) => (
                  <tr key={event.id} className="align-top">
                    <td className="whitespace-nowrap px-4 py-3 text-slate-700">
                      {formatDate(event.created_at)}
                    </td>
                    <td className="px-4 py-3 text-slate-700">{event.actor_email || "—"}</td>
                    <td className="px-4 py-3 font-medium text-slate-900">{event.action}</td>
                    <td className="px-4 py-3 text-slate-700">
                      <div>{event.resource_type}</div>
                      {event.resource_id && (
                        <div className="mt-0.5 font-mono text-xs text-slate-500">
                          {event.resource_id}
                        </div>
                      )}
                    </td>
                    <td className="max-w-md break-all px-4 py-3 font-mono text-xs text-slate-600">
                      {formatMetadata(event.metadata)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
