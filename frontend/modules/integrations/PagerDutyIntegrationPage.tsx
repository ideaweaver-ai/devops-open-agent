"use client";

import { useEffect, useState } from "react";
import { usePagerDutyIntegration } from "@/hooks/usePagerDutyIntegration";
import type { PagerDutyIntegrationSettings } from "@/types/pagerdutyIntegration";

const AGENT_TOGGLES = [
  { key: "notify_kubernetes" as const, label: "Kubernetes Debugging Agent" },
  { key: "notify_aws" as const, label: "AWS DevOps Agent" },
  { key: "notify_cloud_cost" as const, label: "Cloud Cost Detector" },
  { key: "notify_pr_reviewer" as const, label: "PR Reviewer" },
  { key: "notify_performance" as const, label: "Performance Debugging" },
  { key: "notify_security" as const, label: "Security Scanning" },
];

function buildFormState(
  settings: PagerDutyIntegrationSettings | undefined,
): PagerDutyIntegrationSettings {
  return {
    enabled: settings?.enabled ?? false,
    notification_cooldown_minutes: settings?.notification_cooldown_minutes ?? 60,
    notify_kubernetes: settings?.notify_kubernetes ?? true,
    notify_aws: settings?.notify_aws ?? true,
    notify_cloud_cost: settings?.notify_cloud_cost ?? true,
    notify_pr_reviewer: settings?.notify_pr_reviewer ?? true,
    notify_performance: settings?.notify_performance ?? true,
    notify_security: settings?.notify_security ?? true,
  };
}

export function PagerDutyIntegrationPage() {
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
  } = usePagerDutyIntegration();

  const [form, setForm] = useState<PagerDutyIntegrationSettings>(buildFormState(undefined));
  const [routingKeyInput, setRoutingKeyInput] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    if (settings) {
      setForm(buildFormState(settings));
    }
  }, [settings]);

  const updateField = <K extends keyof PagerDutyIntegrationSettings>(
    key: K,
    value: PagerDutyIntegrationSettings[K],
  ) => {
    setForm((current) => ({ ...current, [key]: value }));
    setStatusMessage(null);
  };

  const handleSave = async () => {
    setStatusMessage(null);
    const payload: PagerDutyIntegrationSettings = {
      ...form,
      routing_key: routingKeyInput.trim() ? routingKeyInput.trim() : null,
    };
    await saveSettings(payload);
    setRoutingKeyInput("");
    setStatusMessage("PagerDuty settings saved.");
  };

  const handleTest = async () => {
    setStatusMessage(null);
    await sendTest();
  };

  if (isLoading) {
    return (
      <div className="panel rounded-2xl p-8 text-sm text-slate-400">
        Loading PagerDuty integration settings...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="panel rounded-2xl p-6 sm:p-8">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-white">PagerDuty incidents</h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
              Trigger PagerDuty incidents when AI investigations or PR reviews complete.
              Use an Events API v2 integration key from your PagerDuty service. Instance-level
              defaults apply for GitHub webhook reviews when set by your admin.
            </p>
          </div>
          <label className="inline-flex cursor-pointer items-center gap-3 rounded-xl border border-white/[0.08] bg-slate-900/50 px-4 py-3">
            <span className="text-sm font-medium text-slate-200">Enable notifications</span>
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(event) => updateField("enabled", event.target.checked)}
              className="h-4 w-4 rounded border-white/20 bg-slate-900 text-brand-500 focus:ring-brand-500"
            />
          </label>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-5">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300">
                Integration routing key
              </label>
              <input
                type="password"
                value={routingKeyInput}
                onChange={(event) => setRoutingKeyInput(event.target.value)}
                placeholder={
                  settings?.routing_key_configured
                    ? `Configured ${settings.routing_key_preview ?? ""}`
                    : settings?.instance_routing_key_configured
                      ? "Using instance default — enter a key to override"
                      : "Paste your PagerDuty Events API v2 routing key"
                }
                className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 font-mono text-sm text-white outline-none focus:border-brand-500/40"
              />
              <p className="mt-2 text-xs text-slate-500">
                In PagerDuty: Services → your service → Integrations → Events API V2.
                Leave blank to keep the existing key or use the instance default.
              </p>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300">
                Alert cooldown (minutes)
              </label>
              <input
                type="number"
                min={0}
                max={1440}
                value={form.notification_cooldown_minutes}
                onChange={(event) =>
                  updateField(
                    "notification_cooldown_minutes",
                    Math.max(0, Math.min(1440, Number(event.target.value) || 0)),
                  )
                }
                className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 text-sm text-white outline-none focus:border-brand-500/40"
              />
              <p className="mt-2 text-xs text-slate-500">
                Minimum minutes between PagerDuty incidents for your account. Set to{" "}
                <span className="font-mono text-slate-400">0</span> to disable cooldown.
                Instance default: {settings?.default_cooldown_minutes ?? 60} minutes.
              </p>
            </div>
          </div>

          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5">
            <h3 className="text-sm font-semibold text-white">Notify for these agents</h3>
            <p className="mt-1 text-xs text-slate-500">
              Choose which AI recommendations should trigger PagerDuty incidents.
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
            className="rounded-xl border border-white/[0.1] bg-slate-900/60 px-5 py-2.5 text-sm font-medium text-slate-200 transition hover:border-brand-500/30 hover:text-white disabled:opacity-60"
          >
            {isTesting ? "Sending test..." : "Send test incident"}
          </button>
        </div>

        {statusMessage && (
          <p className="mt-4 text-sm text-emerald-300">{statusMessage}</p>
        )}
        {testResult && (
          <p className="mt-4 text-sm text-emerald-300">{testResult.message}</p>
        )}
        {(saveError || testError) && (
          <p className="mt-4 text-sm text-red-300">
            {(saveError as Error | undefined)?.message ||
              (testError as Error | undefined)?.message ||
              "Something went wrong."}
          </p>
        )}
      </section>

      <section className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6">
        <h2 className="text-lg font-semibold text-white">How it works</h2>
        <ul className="mt-4 space-y-3 text-sm text-slate-400">
          <li>
            When an investigation finishes with AI diagnosis, a PagerDuty incident is triggered
            with root cause, suggested fix, and validation steps in custom details.
          </li>
          <li>
            PR Reviewer triggers an incident with the final recommendation and risk level after
            a review completes.
          </li>
          <li>
            Severity is mapped from AI confidence (investigations) or PR risk rating. Each
            investigation uses a dedup key to avoid duplicate incidents on retries.
          </li>
          <li>
            Alert cooldown limits how often incidents are triggered per user. Investigations
            still complete — only the PagerDuty incident is suppressed until the cooldown expires.
          </li>
          {settings?.instance_routing_key_configured && (
            <li>
              An instance-level routing key is configured and will be used as a fallback for
              unauthenticated events such as GitHub webhooks.
            </li>
          )}
        </ul>
      </section>
    </div>
  );
}
