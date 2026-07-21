"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { useGrafanaIntegration } from "@/hooks/useGrafanaIntegration";
import type { GrafanaIntegrationSettings } from "@/types/grafanaIntegration";

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (!error.response) return "Unable to reach the backend API.";
    return `Request failed with status ${error.response.status}.`;
  }
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

function buildFormState(
  settings: GrafanaIntegrationSettings | undefined,
): GrafanaIntegrationSettings {
  return {
    enabled: settings?.enabled ?? false,
    url: settings?.url ?? "",
    use_kubernetes: settings?.use_kubernetes ?? true,
  };
}

export function GrafanaIntegrationPage() {
  const {
    settings,
    isLoading,
    saveSettings,
    isSaving,
    sendTest,
    isTesting,
    testResult,
    testError,
    saveError,
  } = useGrafanaIntegration();

  const [form, setForm] = useState(buildFormState(undefined));
  const [tokenInput, setTokenInput] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    if (settings) setForm(buildFormState(settings));
  }, [settings]);

  const updateField = <K extends keyof GrafanaIntegrationSettings>(
    key: K,
    value: GrafanaIntegrationSettings[K],
  ) => {
    setForm((current) => ({ ...current, [key]: value }));
    setStatusMessage(null);
  };

  const handleSave = async () => {
    setStatusMessage(null);
    await saveSettings({
      ...form,
      url: form.url.trim(),
      api_token: tokenInput.trim() || null,
    });
    setTokenInput("");
    setStatusMessage("Grafana settings saved.");
  };

  if (isLoading) {
    return (
      <div className="panel rounded-2xl p-8 text-sm text-slate-400">
        Loading Grafana integration settings...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="panel rounded-2xl p-6 sm:p-8">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-white">Grafana</h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
              Pull matching dashboards and recent annotations into Kubernetes
              investigations as evidence for AI diagnosis.
            </p>
          </div>
          <label className="inline-flex cursor-pointer items-center gap-3 rounded-xl border border-white/[0.08] bg-slate-900/50 px-4 py-3">
            <span className="text-sm font-medium text-slate-200">Enable</span>
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(event) => updateField("enabled", event.target.checked)}
              className="h-4 w-4 rounded border-white/20 bg-slate-900 text-brand-500 focus:ring-brand-500"
            />
          </label>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Grafana URL
            </label>
            <input
              type="text"
              value={form.url}
              onChange={(event) => updateField("url", event.target.value)}
              placeholder="http://grafana:3000"
              className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 font-mono text-sm text-white outline-none focus:border-brand-500/40"
            />
            {settings?.instance_url_configured && !form.url.trim() && (
              <p className="mt-2 text-xs text-slate-500">
                An instance-level Grafana endpoint is configured as fallback.
              </p>
            )}
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              API token
            </label>
            <input
              type="password"
              value={tokenInput}
              onChange={(event) => setTokenInput(event.target.value)}
              placeholder={
                settings?.api_token_configured
                  ? `Configured ${settings.api_token_preview ?? ""}`
                  : "Grafana service account / API token"
              }
              className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 font-mono text-sm text-white outline-none focus:border-brand-500/40"
            />
          </div>
        </div>

        <label className="mt-5 flex cursor-pointer items-center justify-between rounded-lg border border-white/[0.06] bg-slate-900/40 px-3 py-2.5">
          <div>
            <span className="block text-sm text-slate-300">
              Prefer Kubernetes dashboard keywords
            </span>
            <span className="mt-0.5 block text-xs text-slate-500">
              Enabled Grafana settings are used for Kubernetes and AWS investigations.
            </span>
          </div>
          <input
            type="checkbox"
            checked={form.use_kubernetes}
            onChange={(event) => updateField("use_kubernetes", event.target.checked)}
            className="h-4 w-4 rounded border-white/20 bg-slate-900 text-brand-500 focus:ring-brand-500"
          />
        </label>

        <div className="mt-8 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={isSaving}
            className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-brand-500 disabled:opacity-60"
          >
            {isSaving ? "Saving..." : "Save settings"}
          </button>
          <button
            type="button"
            onClick={() => void sendTest()}
            disabled={isTesting}
            className="rounded-xl border border-white/[0.10] bg-slate-900/60 px-5 py-2.5 text-sm font-medium text-slate-200 transition hover:border-brand-500/30 hover:text-white disabled:opacity-60"
          >
            {isTesting ? "Testing..." : "Test connection"}
          </button>
        </div>

        {statusMessage && <p className="mt-4 text-sm text-emerald-300">{statusMessage}</p>}
        {testResult && (
          <div className="mt-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
            <p>{testResult.message}</p>
            <p className="mt-1 text-xs text-emerald-300/80">
              {testResult.org_name ? `Org: ${testResult.org_name}` : null}
              {testResult.version ? ` · Version ${testResult.version}` : null}
            </p>
          </div>
        )}
        {(saveError || testError) && (
          <p className="mt-4 text-sm text-red-300">
            {getErrorMessage(saveError ?? testError)}
          </p>
        )}
      </section>
    </div>
  );
}
