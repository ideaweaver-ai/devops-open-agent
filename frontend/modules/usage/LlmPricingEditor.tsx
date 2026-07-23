"use client";

import { useEffect, useMemo, useState } from "react";
import {
  useLlmPricing,
  useResetLlmPricing,
  useSaveLlmPricing,
} from "@/hooks/useLlmPricing";
import type { LlmPricingTable } from "@/types/llmPricing";

type PricingRow = {
  id: string;
  provider: string;
  model: string;
  input_per_1m_usd: string;
  output_per_1m_usd: string;
};

function tableToRows(table: LlmPricingTable): PricingRow[] {
  const rows: PricingRow[] = [];
  for (const [provider, models] of Object.entries(table)) {
    for (const [model, rates] of Object.entries(models)) {
      rows.push({
        id: `${provider}::${model}`,
        provider,
        model,
        input_per_1m_usd: String(rates.input_per_1m_usd ?? 0),
        output_per_1m_usd: String(rates.output_per_1m_usd ?? 0),
      });
    }
  }
  return rows.sort((a, b) =>
    `${a.provider}/${a.model}`.localeCompare(`${b.provider}/${b.model}`),
  );
}

function rowsToTable(rows: PricingRow[]): LlmPricingTable {
  const table: LlmPricingTable = {};
  for (const row of rows) {
    const provider = row.provider.trim().toLowerCase();
    const model = row.model.trim();
    if (!provider || !model) {
      continue;
    }
    if (!table[provider]) {
      table[provider] = {};
    }
    table[provider][model] = {
      input_per_1m_usd: Number(row.input_per_1m_usd || 0),
      output_per_1m_usd: Number(row.output_per_1m_usd || 0),
    };
  }
  return table;
}

export function LlmPricingEditor() {
  const pricingQuery = useLlmPricing();
  const savePricing = useSaveLlmPricing();
  const resetPricing = useResetLlmPricing();
  const [rows, setRows] = useState<PricingRow[]>([]);
  const [loadedPath, setLoadedPath] = useState("");

  useEffect(() => {
    if (!pricingQuery.data) {
      return;
    }
    setRows(tableToRows(pricingQuery.data.table));
    setLoadedPath(pricingQuery.data.source_path);
  }, [pricingQuery.data]);

  const providerCount = useMemo(
    () => new Set(rows.map((row) => row.provider.trim().toLowerCase()).filter(Boolean)).size,
    [rows],
  );

  const updateRow = (id: string, patch: Partial<PricingRow>) => {
    setRows((current) =>
      current.map((row) => (row.id === id ? { ...row, ...patch } : row)),
    );
  };

  const addRow = () => {
    const id = `new-${Date.now()}`;
    setRows((current) => [
      ...current,
      {
        id,
        provider: "openai",
        model: "",
        input_per_1m_usd: "0",
        output_per_1m_usd: "0",
      },
    ]);
  };

  const removeRow = (id: string) => {
    setRows((current) => current.filter((row) => row.id !== id));
  };

  const onSave = async () => {
    const table = rowsToTable(rows);
    await savePricing.mutateAsync(table);
  };

  const onReset = async () => {
    if (!window.confirm("Reset pricing table to bundled defaults?")) {
      return;
    }
    await resetPricing.mutateAsync();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="panel-subtitle mb-1">Usage</p>
          <h1 className="panel-title">LLM pricing</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-600">
            Edit estimated USD rates used for usage metering. Changes persist on the server data
            volume ({loadedPath || "data/pricing_table.json"}). Any authenticated user can edit
            on this self-hosted deploy.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={addRow}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50"
          >
            Add model
          </button>
          <button
            type="button"
            onClick={() => void onReset()}
            disabled={resetPricing.isPending}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:opacity-60"
          >
            {resetPricing.isPending ? "Resetting…" : "Reset defaults"}
          </button>
          <button
            type="button"
            onClick={() => void onSave()}
            disabled={savePricing.isPending}
            className="rounded-lg border border-brand-600 bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {savePricing.isPending ? "Saving…" : "Save pricing"}
          </button>
        </div>
      </div>

      <div className="panel-accent p-4 text-sm text-slate-700">
        {providerCount} provider(s) · {rows.length} model row(s)
      </div>

      {pricingQuery.isLoading && (
        <div className="text-sm text-slate-600">Loading pricing table…</div>
      )}
      {pricingQuery.isError && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          Failed to load pricing table.
        </div>
      )}
      {(savePricing.isError || resetPricing.isError) && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          Failed to update pricing table. Check rates are valid numbers.
        </div>
      )}
      {(savePricing.isSuccess || resetPricing.isSuccess) && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          Pricing table updated.
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Provider</th>
                <th className="px-4 py-3">Model</th>
                <th className="px-4 py-3">Input $/1M</th>
                <th className="px-4 py-3">Output $/1M</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((row) => (
                <tr key={row.id}>
                  <td className="px-4 py-2">
                    <input
                      className="input-field py-1.5 text-sm"
                      value={row.provider}
                      onChange={(event) =>
                        updateRow(row.id, { provider: event.target.value })
                      }
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      className="input-field py-1.5 font-mono text-sm"
                      value={row.model}
                      onChange={(event) => updateRow(row.id, { model: event.target.value })}
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      className="input-field py-1.5 text-sm"
                      value={row.input_per_1m_usd}
                      onChange={(event) =>
                        updateRow(row.id, { input_per_1m_usd: event.target.value })
                      }
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      className="input-field py-1.5 text-sm"
                      value={row.output_per_1m_usd}
                      onChange={(event) =>
                        updateRow(row.id, { output_per_1m_usd: event.target.value })
                      }
                    />
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => removeRow(row.id)}
                      className="text-xs font-semibold text-red-700 hover:underline"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && !pricingQuery.isLoading && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                    No pricing rows. Add a model or reset to defaults.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
