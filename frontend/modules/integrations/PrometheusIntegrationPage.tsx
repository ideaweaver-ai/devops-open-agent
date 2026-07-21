"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { usePrometheusIntegration } from "@/hooks/usePrometheusIntegration";
import type { PrometheusIntegrationSettings } from "@/types/prometheusIntegration";

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
  settings: PrometheusIntegrationSettings | undefined,
): PrometheusIntegrationSettings {
  return {
    enabled: settings?.enabled ?? false,
    url: settings?.url ?? "",
    basic_auth_user: settings?.basic_auth_user ?? "",
    use_kubernetes: settings?.use_kubernetes ?? true,
  };
}

export function PrometheusIntegrationPage() {
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
  } = usePrometheusIntegration();

  const [form, setForm] = useState(buildFormState(undefined));
  const [bearerInput, setBearerInput] = useState("");
  const [passwordInput, setPasswordInput] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    if (settings) setForm(buildFormState(settings));
  }, [settings]);

  const updateField = <K extends keyof PrometheusIntegrationSettings>(
    key: K,
    value: PrometheusIntegrationSettings[K],
  ) => {
    setForm((current) => ({ ...current, [key]: value }));
    setStatusMessage(null);
  };

  const handleSave = async () => {
    setStatusMessage(null);
    await saveSettings({
      ...form,
      url: form.url.trim(),
      basic_auth_user: form.basic_auth_user?.trim() || null,
      bearer_token: bearerInput.trim() || null,
      basic_auth_password: passwordInput.trim() || null,
    });
    setBearerInput("");
    setPasswordInput("");
    setStatusMessage("Prometheus settings saved.");
  };

  if (isLoading) {
    return (
      <div className="panel rounded-2xl p-8 text-sm text-slate-400">
        Loading Prometheus integration settings...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="panel rounded-2xl p-6 sm:p-8">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-white">Prometheus</h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
              Pull curated Kubernetes metrics (restarts, OOM kills, CPU/memory) into
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
              Prometheus URL
            </label>
            <input
              type="text"
              value={form.url}
              onChange={(event) => updateField("url", event.target.value)}
              placeholder="http://prometheus:9090"
              className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 font-mono text-sm text-white outline-none focus:border-brand-500/40"
            />
            {settings?.instance_url_configured && !form.url.trim() && (
              <p className="mt-2 text-xs text-slate-500">
                An instance-level Prometheus endpoint is configured as fallback.
              </p>
            )}
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Bearer token (optional)
            </label>
            <input
              type="password"
              value={bearerInput}
              onChange={(event) => setBearerInput(event.target.value)}
              placeholder={
                settings?.bearer_token_configured
                  ? `Configured ${settings.bearer_token_preview ?? ""}`
                  : "Optional"
              }
              className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 font-mono text-sm text-white outline-none focus:border-brand-500/40"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Basic auth username (optional)
            </label>
            <input
              type="text"
              value={form.basic_auth_user ?? ""}
              onChange={(event) => updateField("basic_auth_user", event.target.value)}
              className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 font-mono text-sm text-white outline-none focus:border-brand-500/40"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Basic auth password (optional)
            </label>
            <input
              type="password"
              value={passwordInput}
              onChange={(event) => setPasswordInput(event.target.value)}
              placeholder={
                settings?.basic_auth_password_configured ? "Configured (hidden)" : "Optional"
              }
              className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 font-mono text-sm text-white outline-none focus:border-brand-500/40"
            />
          </div>
        </div>

        <label className="mt-5 flex cursor-pointer items-center justify-between rounded-lg border border-white/[0.06] bg-slate-900/40 px-3 py-2.5">
          <div>
            <span className="block text-sm text-slate-300">
              Prefer Kubernetes-oriented PromQL
            </span>
            <span className="mt-0.5 block text-xs text-slate-500">
              Enabled integrations are used for Kubernetes and AWS investigations. Host/EC2
              metrics are always queried when available.
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
            {testResult.version && (
              <p className="mt-1 text-xs text-emerald-300/80">Version {testResult.version}</p>
            )}
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
