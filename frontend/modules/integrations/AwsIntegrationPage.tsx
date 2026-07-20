"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { useAwsIntegration } from "@/hooks/useAwsIntegration";
import type { AwsAccountSettings } from "@/types/awsIntegration";

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.code === "ECONNABORTED") {
      return "Connection test timed out while calling STS AssumeRole.";
    }
    if (!error.response) return "Unable to reach the backend API.";
    return `Request failed with status ${error.response.status}.`;
  }
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

type AccountFormRow = AwsAccountSettings & {
  externalIdInput: string;
  clearExternalId: boolean;
};

function emptyAccount(): AccountFormRow {
  return {
    id: null,
    label: "",
    account_id: "",
    role_arn: "",
    default_region: "us-east-1",
    enabled: true,
    externalIdInput: "",
    clearExternalId: false,
  };
}

export function AwsIntegrationPage() {
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
  } = useAwsIntegration();

  const [enabled, setEnabled] = useState(false);
  const [accounts, setAccounts] = useState<AccountFormRow[]>([emptyAccount()]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [testAccountId, setTestAccountId] = useState<string>("");

  useEffect(() => {
    if (!settings) return;
    setEnabled(settings.enabled);
    if (settings.accounts.length === 0) {
      setAccounts([emptyAccount()]);
      return;
    }
    setAccounts(
      settings.accounts.map((account) => ({
        id: account.id,
        label: account.label,
        account_id: account.account_id,
        role_arn: account.role_arn,
        default_region: account.default_region || "us-east-1",
        enabled: account.enabled,
        externalIdInput: "",
        clearExternalId: false,
      })),
    );
  }, [settings]);

  const updateAccount = <K extends keyof AccountFormRow>(
    index: number,
    key: K,
    value: AccountFormRow[K],
  ) => {
    setAccounts((current) =>
      current.map((row, i) => (i === index ? { ...row, [key]: value } : row)),
    );
    setStatusMessage(null);
  };

  const handleSave = async () => {
    setStatusMessage(null);
    await saveSettings({
      enabled,
      accounts: accounts
        .filter((row) => row.account_id.trim() && row.role_arn.trim())
        .map((row) => ({
          id: row.id,
          label: row.label.trim(),
          account_id: row.account_id.trim(),
          role_arn: row.role_arn.trim(),
          default_region: row.default_region?.trim() || null,
          enabled: row.enabled,
          external_id: row.clearExternalId
            ? ""
            : row.externalIdInput.trim() || null,
        })),
    });
    setStatusMessage("AWS account settings saved.");
  };

  const handleTest = async () => {
    setStatusMessage(null);
    await sendTest(testAccountId ? { account_id: testAccountId } : undefined);
  };

  if (isLoading) {
    return (
      <div className="panel rounded-2xl p-8 text-sm text-slate-400">
        Loading AWS multi-account settings...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="panel rounded-2xl p-6 sm:p-8">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-white">AWS Accounts</h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
              Configure target accounts via STS AssumeRole. Hub credentials remain your local
              ~/.aws / AWS_PROFILE / IAM role. Investigations and topology use the selected
              account&apos;s role when it is not the hub identity.
            </p>
          </div>
          <label className="inline-flex cursor-pointer items-center gap-3 rounded-xl border border-white/[0.08] bg-slate-900/50 px-4 py-3">
            <span className="text-sm font-medium text-slate-200">Enable</span>
            <input
              type="checkbox"
              checked={enabled}
              onChange={(event) => {
                setEnabled(event.target.checked);
                setStatusMessage(null);
              }}
              className="h-4 w-4 rounded border-white/20 bg-slate-900 text-brand-500 focus:ring-brand-500"
            />
          </label>
        </div>

        <div className="space-y-4">
          {accounts.map((account, index) => (
            <div
              key={account.id ?? `new-${index}`}
              className="rounded-xl border border-white/[0.08] bg-slate-900/40 p-4"
            >
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-slate-200">
                  Account {index + 1}
                  {account.label ? ` — ${account.label}` : ""}
                </p>
                <div className="flex items-center gap-3">
                  <label className="inline-flex items-center gap-2 text-xs text-slate-400">
                    Enabled
                    <input
                      type="checkbox"
                      checked={account.enabled}
                      onChange={(event) =>
                        updateAccount(index, "enabled", event.target.checked)
                      }
                      className="h-3.5 w-3.5 rounded border-white/20 bg-slate-900 text-brand-500"
                    />
                  </label>
                  {accounts.length > 1 && (
                    <button
                      type="button"
                      onClick={() =>
                        setAccounts((current) => current.filter((_, i) => i !== index))
                      }
                      className="text-xs text-slate-400 underline hover:text-slate-200"
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>

              <div className="grid gap-3 lg:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400">Label</label>
                  <input
                    type="text"
                    value={account.label}
                    onChange={(event) => updateAccount(index, "label", event.target.value)}
                    placeholder="prod-security"
                    className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-3 py-2.5 font-mono text-sm text-white outline-none focus:border-brand-500/40"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400">
                    Account ID
                  </label>
                  <input
                    type="text"
                    value={account.account_id}
                    onChange={(event) =>
                      updateAccount(index, "account_id", event.target.value)
                    }
                    placeholder="123456789012"
                    className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-3 py-2.5 font-mono text-sm text-white outline-none focus:border-brand-500/40"
                  />
                </div>
                <div className="lg:col-span-2">
                  <label className="mb-1 block text-xs font-medium text-slate-400">
                    Role ARN
                  </label>
                  <input
                    type="text"
                    value={account.role_arn}
                    onChange={(event) => updateAccount(index, "role_arn", event.target.value)}
                    placeholder="arn:aws:iam::123456789012:role/DevOpsOpenAgentReadOnly"
                    className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-3 py-2.5 font-mono text-sm text-white outline-none focus:border-brand-500/40"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400">
                    External ID (optional)
                  </label>
                  <input
                    type="password"
                    value={account.externalIdInput}
                    disabled={account.clearExternalId}
                    onChange={(event) => {
                      updateAccount(index, "clearExternalId", false);
                      updateAccount(index, "externalIdInput", event.target.value);
                    }}
                    placeholder={
                      account.clearExternalId
                        ? "Will clear on save"
                        : settings?.accounts.find((a) => a.id === account.id)
                              ?.external_id_configured
                          ? `Configured ${
                              settings.accounts.find((a) => a.id === account.id)
                                ?.external_id_preview ?? ""
                            }`
                          : "Optional"
                    }
                    className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-3 py-2.5 font-mono text-sm text-white outline-none focus:border-brand-500/40 disabled:opacity-60"
                  />
                  {settings?.accounts.find((a) => a.id === account.id)
                    ?.external_id_configured &&
                    !account.clearExternalId && (
                      <button
                        type="button"
                        onClick={() => {
                          updateAccount(index, "externalIdInput", "");
                          updateAccount(index, "clearExternalId", true);
                        }}
                        className="mt-1 text-xs text-slate-400 underline hover:text-slate-200"
                      >
                        Clear saved external ID
                      </button>
                    )}
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400">
                    Default region
                  </label>
                  <input
                    type="text"
                    value={account.default_region ?? ""}
                    onChange={(event) =>
                      updateAccount(index, "default_region", event.target.value)
                    }
                    placeholder="us-east-1"
                    className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-3 py-2.5 font-mono text-sm text-white outline-none focus:border-brand-500/40"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={() => setAccounts((current) => [...current, emptyAccount()])}
          className="mt-4 text-sm text-brand-300 underline hover:text-brand-200"
        >
          Add account
        </button>

        <div className="mt-8 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={isSaving}
            className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-brand-500 disabled:opacity-60"
          >
            {isSaving ? "Saving..." : "Save settings"}
          </button>
          <select
            value={testAccountId}
            onChange={(event) => setTestAccountId(event.target.value)}
            className="rounded-xl border border-white/[0.10] bg-slate-900/60 px-3 py-2.5 text-sm text-slate-200"
          >
            <option value="">Test first enabled account</option>
            {(settings?.accounts ?? [])
              .filter((a) => a.enabled)
              .map((account) => (
                <option key={account.id} value={account.account_id}>
                  {account.label || account.account_id}
                </option>
              ))}
          </select>
          <button
            type="button"
            onClick={() => void handleTest()}
            disabled={isTesting}
            className="rounded-xl border border-white/[0.10] bg-slate-900/60 px-5 py-2.5 text-sm font-medium text-slate-200 transition hover:border-brand-500/30 hover:text-white disabled:opacity-60"
          >
            {isTesting ? "Testing..." : "Test AssumeRole"}
          </button>
        </div>

        {statusMessage && <p className="mt-4 text-sm text-emerald-300">{statusMessage}</p>}
        {testResult && (
          <div className="mt-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
            <p>{testResult.message}</p>
            {testResult.caller_arn && (
              <p className="mt-1 font-mono text-xs text-emerald-300/80">
                {testResult.caller_arn}
              </p>
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
