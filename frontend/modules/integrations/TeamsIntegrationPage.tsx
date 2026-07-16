"use client";

import { useEffect, useState } from "react";
import { useTeamsIntegration } from "@/hooks/useTeamsIntegration";
import type { TeamsIntegrationSettings } from "@/types/teamsIntegration";

const AGENT_TOGGLES = [
  { key: "notify_kubernetes" as const, label: "Kubernetes Debugging Agent" },
  { key: "notify_aws" as const, label: "AWS DevOps Agent" },
  { key: "notify_cloud_cost" as const, label: "Cloud Cost Detector" },
  { key: "notify_pr_reviewer" as const, label: "PR Reviewer" },
  { key: "notify_performance" as const, label: "Performance Debugging" },
  { key: "notify_security" as const, label: "Security Scanning" },
];

function buildFormState(
  settings: TeamsIntegrationSettings | undefined,
): TeamsIntegrationSettings {
  return {
    enabled: settings?.enabled ?? false,
    notify_kubernetes: settings?.notify_kubernetes ?? true,
    notify_aws: settings?.notify_aws ?? true,
    notify_cloud_cost: settings?.notify_cloud_cost ?? true,
    notify_pr_reviewer: settings?.notify_pr_reviewer ?? true,
    notify_performance: settings?.notify_performance ?? true,
    notify_security: settings?.notify_security ?? true,
  };
}

export function TeamsIntegrationPage() {
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
  } = useTeamsIntegration();

  const [form, setForm] = useState<TeamsIntegrationSettings>(buildFormState(undefined));
  const [webhookInput, setWebhookInput] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    if (settings) {
      setForm(buildFormState(settings));
    }
  }, [settings]);

  const updateField = <K extends keyof TeamsIntegrationSettings>(
    key: K,
    value: TeamsIntegrationSettings[K],
  ) => {
    setForm((current) => ({ ...current, [key]: value }));
    setStatusMessage(null);
  };

  const handleSave = async () => {
    setStatusMessage(null);
    const payload: TeamsIntegrationSettings = {
      ...form,
      webhook_url: webhookInput.trim() ? webhookInput.trim() : null,
    };
    await saveSettings(payload);
    setWebhookInput("");
    setStatusMessage("Microsoft Teams settings saved.");
  };

  const handleTest = async () => {
    setStatusMessage(null);
    await sendTest();
  };

  if (isLoading) {
    return (
      <div className="panel rounded-2xl p-8 text-sm text-slate-400">
        Loading Microsoft Teams integration settings...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="panel rounded-2xl p-6 sm:p-8">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-white">Microsoft Teams alerts</h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
              Post AI recommendations to a Teams channel when investigations or PR reviews
              complete. Paste an incoming webhook URL from your Teams channel — the same
              simple setup as Slack webhooks.
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
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Incoming webhook URL
            </label>
            <input
              type="password"
              value={webhookInput}
              onChange={(event) => setWebhookInput(event.target.value)}
              placeholder={
                settings?.webhook_url_configured
                  ? `Configured ${settings.webhook_url_preview ?? ""}`
                  : "https://outlook.office.com/webhook/..."
              }
              className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 font-mono text-sm text-white outline-none focus:border-brand-500/40"
            />
            <p className="mt-2 text-xs text-slate-500">
              In Teams: open your channel → Connectors → Incoming Webhook (or use a Power
              Automate workflow webhook). Leave blank to keep the existing webhook.
            </p>
          </div>

          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5">
            <h3 className="text-sm font-semibold text-white">Notify for these agents</h3>
            <p className="mt-1 text-xs text-slate-500">
              Choose which AI recommendations should be posted to Teams.
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
            className="rounded-xl border border-white/[0.10] bg-slate-900/60 px-5 py-2.5 text-sm font-medium text-slate-200 transition hover:border-brand-500/30 hover:text-white disabled:opacity-60"
          >
            {isTesting ? "Sending test..." : "Send test message"}
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
            When an investigation finishes with AI diagnosis enabled, root cause, suggested fix,
            and validation steps are posted to your Teams channel.
          </li>
          <li>
            PR Reviewer posts the final recommendation and risk summary after a review completes.
          </li>
          <li>
            Webhook delivery is the simplest setup — paste your Teams incoming webhook URL and
            send a test message to confirm.
          </li>
          <li>
            To prevent alert fatigue, Teams posts are limited to once per hour per user.
            Investigations still run on schedule — results appear in Investigations even when
            Teams is temporarily suppressed.
          </li>
          {settings?.instance_webhook_configured && (
            <li>
              An instance-level webhook is configured and will be used as a fallback for
              unauthenticated events such as GitHub webhooks.
            </li>
          )}
        </ul>
      </section>
    </div>
  );
}
