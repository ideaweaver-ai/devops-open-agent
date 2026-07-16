"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { useQdrantIntegration } from "@/hooks/useQdrantIntegration";
import type { QdrantIntegrationSettings } from "@/types/qdrantIntegration";

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (!error.response) {
      return "Unable to reach the backend API.";
    }
    return `Request failed with status ${error.response.status}.`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong.";
}

const AGENT_TOGGLES = [
  { key: "use_kubernetes" as const, label: "Kubernetes Debugging Agent" },
  { key: "use_aws" as const, label: "AWS DevOps Agent" },
  { key: "use_cloud_cost" as const, label: "Cloud Cost Detector" },
  { key: "use_performance" as const, label: "Performance Debugging" },
  { key: "use_security" as const, label: "Security Scanning" },
];

function buildFormState(
  settings: QdrantIntegrationSettings | undefined,
): QdrantIntegrationSettings {
  return {
    enabled: settings?.enabled ?? false,
    url: settings?.url ?? "",
    collection: settings?.collection ?? "",
    use_kubernetes: settings?.use_kubernetes ?? true,
    use_aws: settings?.use_aws ?? true,
    use_cloud_cost: settings?.use_cloud_cost ?? true,
    use_performance: settings?.use_performance ?? true,
    use_security: settings?.use_security ?? true,
  };
}

export function QdrantIntegrationPage() {
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
  } = useQdrantIntegration();

  const [form, setForm] = useState<QdrantIntegrationSettings>(buildFormState(undefined));
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    if (settings) {
      setForm(buildFormState(settings));
    }
  }, [settings]);

  const updateField = <K extends keyof QdrantIntegrationSettings>(
    key: K,
    value: QdrantIntegrationSettings[K],
  ) => {
    setForm((current) => ({ ...current, [key]: value }));
    setStatusMessage(null);
  };

  const handleSave = async () => {
    setStatusMessage(null);
    const payload: QdrantIntegrationSettings = {
      ...form,
      url: form.url.trim(),
      collection: form.collection?.trim() ? form.collection.trim() : null,
      api_key: apiKeyInput.trim() ? apiKeyInput.trim() : null,
    };
    await saveSettings(payload);
    setApiKeyInput("");
    setStatusMessage("Qdrant settings saved.");
  };

  const handleTest = async () => {
    setStatusMessage(null);
    await sendTest();
  };

  if (isLoading) {
    return (
      <div className="panel rounded-2xl p-8 text-sm text-slate-400">
        Loading Qdrant integration settings...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="panel rounded-2xl p-6 sm:p-8">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-white">
              Qdrant vector database (RAG)
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
              Store every completed investigation as a vector in Qdrant. When you run a
              Kubernetes or AWS investigation with{" "}
              <span className="text-slate-200">Include past investigations (RAG)</span>{" "}
              enabled, the agent retrieves the most similar prior cases and factors them
              into the analysis.
            </p>
          </div>
          <label className="inline-flex cursor-pointer items-center gap-3 rounded-xl border border-white/[0.08] bg-slate-900/50 px-4 py-3">
            <span className="text-sm font-medium text-slate-200">Enable RAG</span>
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(event) => updateField("enabled", event.target.checked)}
              className="h-4 w-4 rounded border-white/20 bg-slate-900 text-brand-500 focus:ring-brand-500"
            />
          </label>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-4">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300">
                Qdrant URL
              </label>
              <input
                type="text"
                value={form.url}
                onChange={(event) => updateField("url", event.target.value)}
                placeholder="http://qdrant:6333 or https://<cluster>.qdrant.io"
                className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 font-mono text-sm text-white outline-none focus:border-brand-500/40"
              />
              {settings?.instance_url_configured && !form.url.trim() && (
                <p className="mt-2 text-xs text-slate-500">
                  An instance-level Qdrant endpoint is configured and will be used by
                  default.
                </p>
              )}
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300">
                API key (optional)
              </label>
              <input
                type="password"
                value={apiKeyInput}
                onChange={(event) => setApiKeyInput(event.target.value)}
                placeholder={
                  settings?.api_key_configured
                    ? `Configured ${settings.api_key_preview ?? ""}`
                    : "Leave blank for local / unauthenticated Qdrant"
                }
                className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 font-mono text-sm text-white outline-none focus:border-brand-500/40"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300">
                Collection (optional)
              </label>
              <input
                type="text"
                value={form.collection ?? ""}
                onChange={(event) => updateField("collection", event.target.value)}
                placeholder={settings?.collection ?? "devops_open_agent_investigations"}
                className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 font-mono text-sm text-white outline-none focus:border-brand-500/40"
              />
            </div>
          </div>

          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5">
            <h3 className="text-sm font-semibold text-white">Store investigations for</h3>
            <p className="mt-1 text-xs text-slate-500">
              Completed investigations for these agents are indexed into Qdrant and made
              available for retrieval.
            </p>
            <div className="mt-4 space-y-3">
              {AGENT_TOGGLES.map((toggle) => (
                <label
                  key={toggle.key}
                  className="flex cursor-pointer items-center justify-between rounded-lg border border-white/[0.06] bg-slate-900/40 px-3 py-2.5"
                >
                  <span className="text-sm text-slate-300">{toggle.label}</span>
                  <input
                    type="checkbox"
                    checked={form[toggle.key]}
                    onChange={(event) => updateField(toggle.key, event.target.checked)}
                    className="h-4 w-4 rounded border-white/20 bg-slate-900 text-brand-500 focus:ring-brand-500"
                  />
                </label>
              ))}
            </div>

            <div className="mt-5 rounded-lg border border-white/[0.06] bg-slate-900/40 px-3 py-2.5">
              <p className="text-xs text-slate-500">Embedding model</p>
              <p className="mt-1 font-mono text-xs text-slate-300">
                {settings?.embedding_provider ?? "-"} / {settings?.embedding_model ?? "-"}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-brand-500 disabled:opacity-60"
          >
            {isSaving ? "Saving..." : "Save settings"}
          </button>
          <button
            type="button"
            onClick={handleTest}
            disabled={isTesting}
            className="rounded-xl border border-white/[0.10] bg-slate-900/60 px-5 py-2.5 text-sm font-medium text-slate-200 transition hover:border-brand-500/30 hover:text-white disabled:opacity-60"
          >
            {isTesting ? "Testing..." : "Test connection"}
          </button>
        </div>

        {statusMessage && (
          <p className="mt-4 text-sm text-emerald-300">{statusMessage}</p>
        )}
        {testResult && (
          <div className="mt-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
            <p>{testResult.message}</p>
            <p className="mt-1 text-xs text-emerald-300/80">
              Collection <span className="font-mono">{testResult.collection}</span>
              {testResult.vector_count != null &&
                ` · ${testResult.vector_count} vectors stored`}
              {testResult.embedding_provider &&
                ` · embeddings: ${testResult.embedding_provider} (${testResult.embedding_dimension} dims)`}
            </p>
          </div>
        )}
        {(saveError || testError) && (
          <p className="mt-4 text-sm text-red-300">
            {getErrorMessage(saveError ?? testError)}
          </p>
        )}
      </section>

      <section className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6">
        <h2 className="text-lg font-semibold text-white">How it works</h2>
        <ul className="mt-4 space-y-3 text-sm text-slate-400">
          <li>
            Each completed investigation with an AI diagnosis is embedded and upserted into
            your Qdrant collection, tagged by agent type and user.
          </li>
          <li>
            On the Kubernetes and AWS pages, tick{" "}
            <span className="text-slate-200">Include past investigations (RAG)</span> to
            retrieve the most similar prior cases and feed them to the LLM as extra context.
          </li>
          <li>
            Retrieval is scoped to your own investigations, so recommendations build on the
            history your team has actually seen.
          </li>
          <li>
            Embeddings reuse your configured LLM provider (OpenAI, Gemini, or Ollama) — no
            extra credentials required beyond the Qdrant endpoint.
          </li>
        </ul>
      </section>
    </div>
  );
}
