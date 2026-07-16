"use client";

import { useEffect, useState } from "react";
import { useMcpIntegration } from "@/hooks/useMcpIntegration";
import type { McpIntegrationSettings, McpOfficialServer } from "@/types/mcpIntegration";
import { McpAskResultPanel } from "@/modules/integrations/McpAskResultPanel";

const AGENT_TOGGLES = [
  { key: "use_kubernetes" as const, label: "Kubernetes Debugging Agent" },
  { key: "use_aws" as const, label: "AWS DevOps Agent" },
  { key: "use_cloud_cost" as const, label: "Cloud Cost Detector" },
  { key: "use_pr_reviewer" as const, label: "PR Reviewer" },
  { key: "use_performance" as const, label: "Performance Debugging" },
  { key: "use_security" as const, label: "Security Scanning" },
];

function getErrorMessage(error: unknown): string {
  if (error && typeof error === "object" && "response" in error) {
    const axiosError = error as {
      response?: { data?: { detail?: unknown } };
      message?: string;
    };
    const detail = axiosError.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (axiosError.message && axiosError.message !== "Network Error") {
      return axiosError.message;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong.";
}

function normalizeUrl(url: string): string {
  return url.trim().replace(/\/+$/, "");
}

function findOfficialServerByUrl(
  serverUrl: string,
  officialServers: McpOfficialServer[],
): McpOfficialServer | undefined {
  const normalized = normalizeUrl(serverUrl);
  if (!normalized) {
    return undefined;
  }
  return officialServers.find(
    (server) => normalizeUrl(server.server_url) === normalized,
  );
}

function buildFormState(
  settings: McpIntegrationSettings | undefined,
): McpIntegrationSettings {
  return {
    enabled: settings?.enabled ?? false,
    server_url: settings?.server_url ?? "",
    use_kubernetes: settings?.use_kubernetes ?? true,
    use_aws: settings?.use_aws ?? true,
    use_cloud_cost: settings?.use_cloud_cost ?? true,
    use_pr_reviewer: settings?.use_pr_reviewer ?? true,
    use_performance: settings?.use_performance ?? true,
    use_security: settings?.use_security ?? true,
  };
}

export function McpIntegrationPage() {
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
    askQuestion,
    isAsking,
    askResult,
    askError,
    addWhitelistEntry,
    isAddingWhitelist,
    addWhitelistError,
    removeWhitelistEntry,
    isRemovingWhitelist,
    addBlacklistEntry,
    isAddingBlacklist,
    addBlacklistError,
    removeBlacklistEntry,
    isRemovingBlacklist,
  } = useMcpIntegration();

  const [form, setForm] = useState<McpIntegrationSettings>(buildFormState(undefined));
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [whitelistName, setWhitelistName] = useState("");
  const [whitelistUrl, setWhitelistUrl] = useState("");
  const [blacklistUrl, setBlacklistUrl] = useState("");
  const [selectedOfficialId, setSelectedOfficialId] = useState("");

  const officialServers = settings?.official_servers ?? [];
  const whitelist = settings?.whitelist ?? [];
  const blacklist = settings?.blacklist ?? [];
  const hasWhitelist = whitelist.length > 0;

  useEffect(() => {
    if (settings) {
      setForm(buildFormState(settings));
      const matched = findOfficialServerByUrl(
        settings.server_url,
        settings.official_servers,
      );
      setSelectedOfficialId(matched?.id ?? (settings.server_url.trim() ? "custom" : ""));
    }
  }, [settings]);

  const updateField = <K extends keyof McpIntegrationSettings>(
    key: K,
    value: McpIntegrationSettings[K],
  ) => {
    setForm((current) => ({ ...current, [key]: value }));
    setStatusMessage(null);
  };

  const handleSave = async () => {
    setStatusMessage(null);
    const payload: McpIntegrationSettings = {
      ...form,
      api_key: apiKeyInput.trim() ? apiKeyInput.trim() : null,
    };
    await saveSettings(payload);
    setApiKeyInput("");
    setStatusMessage("MCP settings saved.");
  };

  const handleTest = async () => {
    setStatusMessage(null);
    await sendTest();
  };

  const handleAsk = async () => {
    const trimmed = question.trim();
    if (!trimmed) {
      return;
    }
    await askQuestion(trimmed);
  };

  const handleAddWhitelist = async () => {
    setStatusMessage(null);
    await addWhitelistEntry({
      name: whitelistName.trim(),
      server_url: whitelistUrl.trim(),
    });
    setWhitelistName("");
    setWhitelistUrl("");
    setStatusMessage("MCP server added to your whitelist.");
  };

  const handleAddBlacklist = async () => {
    setStatusMessage(null);
    await addBlacklistEntry({ server_url: blacklistUrl.trim() });
    setBlacklistUrl("");
    setStatusMessage("MCP server added to your blacklist.");
  };

  const handleOfficialServerChange = (officialId: string) => {
    setSelectedOfficialId(officialId);
    setStatusMessage(null);

    if (!officialId) {
      return;
    }

    if (officialId === "custom") {
      return;
    }

    const official = officialServers.find((server) => server.id === officialId);
    if (!official) {
      return;
    }

    if (hasWhitelist) {
      const whitelisted = whitelist.find(
        (entry) => normalizeUrl(entry.server_url) === normalizeUrl(official.server_url),
      );
      if (whitelisted) {
        updateField("server_url", whitelisted.server_url);
        return;
      }
      setWhitelistName(official.name);
      setWhitelistUrl(official.server_url);
      setStatusMessage(
        `Add "${official.name}" to your whitelist, then select it as the active server.`,
      );
      return;
    }

    updateField("server_url", official.server_url);
  };

  const handleOfficialWhitelistPick = (officialId: string) => {
    if (!officialId) {
      return;
    }
    const official = officialServers.find((server) => server.id === officialId);
    if (!official) {
      return;
    }
    setWhitelistName(official.name);
    setWhitelistUrl(official.server_url);
  };

  const selectedOfficial = officialServers.find(
    (server) => server.id === selectedOfficialId,
  );

  const instanceRestricted = settings?.instance_url_restrictions_enabled ?? false;

  const mcpReady = Boolean(
    settings?.enabled &&
      (settings.server_url.trim() || settings.instance_server_configured),
  );

  if (isLoading) {
    return (
      <div className="panel rounded-2xl p-8 text-sm text-slate-400">
        Loading MCP integration settings...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="panel rounded-2xl p-6 sm:p-8">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-white">MCP server</h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
              Connect a Model Context Protocol (MCP) server to query external tools directly or
              enrich AI investigations with discovered tools and resources.
            </p>
          </div>
          <label className="inline-flex cursor-pointer items-center gap-3 rounded-xl border border-white/[0.08] bg-slate-900/50 px-4 py-3">
            <span className="text-sm font-medium text-slate-200">Enable MCP</span>
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(event) => updateField("enabled", event.target.checked)}
              className="h-4 w-4 rounded border-white/20 bg-slate-900 text-brand-500 focus:ring-brand-500"
            />
          </label>
        </div>

        {instanceRestricted && (
          <div className="mb-6 rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
            <p className="font-medium">Platform URL restrictions are enabled</p>
            <p className="mt-1 text-amber-100/80">
              Only MCP servers matching the administrator allowlist can be used:
            </p>
            <ul className="mt-2 space-y-1 font-mono text-xs text-amber-100/90">
              {settings?.instance_allowed_urls.map((url) => (
                <li key={url}>{url}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-5">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300">
                Official MCP server
              </label>
              <select
                value={selectedOfficialId}
                onChange={(event) => handleOfficialServerChange(event.target.value)}
                className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 text-sm text-white outline-none focus:border-brand-500/40"
              >
                <option value="">Select an official server...</option>
                {officialServers.map((server) => (
                  <option key={server.id} value={server.id}>
                    {server.name}
                  </option>
                ))}
                <option value="custom">Custom URL</option>
              </select>
              {selectedOfficial && (
                <div className="mt-3 rounded-xl border border-brand-500/20 bg-brand-500/5 px-4 py-3 text-xs text-slate-300">
                  <p>{selectedOfficial.description}</p>
                  <p className="mt-2 text-slate-400">
                    Auth: <span className="text-slate-300">{selectedOfficial.auth_hint}</span>
                  </p>
                  <a
                    href={selectedOfficial.docs_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-block text-brand-300 hover:text-brand-200"
                  >
                    View official docs
                  </a>
                </div>
              )}
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300">
                Active MCP server
              </label>
              {hasWhitelist ? (
                <select
                  value={form.server_url}
                  onChange={(event) => updateField("server_url", event.target.value)}
                  className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 text-sm text-white outline-none focus:border-brand-500/40"
                >
                  <option value="">Select a whitelisted server</option>
                  {whitelist.map((entry) => (
                    <option key={entry.id} value={entry.server_url}>
                      {entry.name} — {entry.server_url}
                    </option>
                  ))}
                </select>
              ) : selectedOfficialId === "custom" || !selectedOfficialId ? (
                <input
                  type="url"
                  value={form.server_url}
                  onChange={(event) => updateField("server_url", event.target.value)}
                  placeholder={
                    settings?.instance_server_configured
                      ? "https://your-mcp-server.example/mcp (or use instance default)"
                      : "https://your-mcp-server.example/mcp"
                  }
                  className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 font-mono text-sm text-white outline-none focus:border-brand-500/40"
                />
              ) : (
                <input
                  type="url"
                  value={form.server_url}
                  readOnly
                  className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 font-mono text-sm text-slate-300 outline-none"
                />
              )}
              <p className="mt-2 text-xs text-slate-500">
                {hasWhitelist
                  ? "Choose a server from your whitelist. Pick an official server above to pre-fill a whitelist entry."
                  : selectedOfficialId && selectedOfficialId !== "custom"
                    ? "Official server URL selected from the supported catalog."
                    : "Pick an official server above or enter a custom Streamable HTTP endpoint."}
              </p>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300">
                API key{selectedOfficial?.auth_hint ? " (required)" : " (optional)"}
              </label>
              <input
                type="password"
                value={apiKeyInput}
                onChange={(event) => setApiKeyInput(event.target.value)}
                placeholder={
                  settings?.api_key_configured
                    ? `Configured ${settings.api_key_preview ?? ""}`
                    : selectedOfficial?.auth_hint
                      ? `Paste your ${selectedOfficial.auth_hint}`
                      : "Bearer token for authenticated MCP servers"
                }
                className="w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 font-mono text-sm text-white outline-none focus:border-brand-500/40"
              />
              <p className="mt-2 text-xs text-slate-500">
                Sent as <span className="font-mono text-slate-400">Authorization: Bearer …</span>.
                {settings?.api_key_configured
                  ? " Leave blank to keep the existing key. Enter a new value to replace it."
                  : selectedOfficial?.auth_hint
                    ? ` Required for ${selectedOfficial.name}.`
                    : ""}
              </p>
            </div>
          </div>

          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5">
            <h3 className="text-sm font-semibold text-white">Use MCP for these agents</h3>
            <p className="mt-1 text-xs text-slate-500">
              When enabled, AI diagnosis will include tools and resources from your MCP server.
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
            {isTesting ? "Testing..." : "Test connection"}
          </button>
        </div>

        {statusMessage && (
          <p className="mt-4 text-sm text-emerald-300">{statusMessage}</p>
        )}
        {testResult && (
          <div className="mt-4 space-y-2 text-sm text-emerald-300">
            <p>{testResult.message}</p>
            {testResult.tools.length > 0 && (
              <p className="text-slate-400">
                Sample tools: {testResult.tools.join(", ")}
              </p>
            )}
          </div>
        )}
        {(saveError || testError) && (
          <p className="mt-4 text-sm text-red-300">
            {getErrorMessage(saveError) || getErrorMessage(testError)}
          </p>
        )}
      </section>

      <section className="panel rounded-2xl p-6 sm:p-8">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-white">Trusted MCP servers (whitelist)</h2>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Save MCP servers you trust with a friendly name. Once you add whitelist entries,
            you can only connect to servers on this list.
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-4">
          <select
            defaultValue=""
            onChange={(event) => handleOfficialWhitelistPick(event.target.value)}
            className="rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 text-sm text-white outline-none focus:border-brand-500/40"
          >
            <option value="">Official server...</option>
            {officialServers.map((server) => (
              <option key={server.id} value={server.id}>
                {server.name}
              </option>
            ))}
          </select>
          <input
            type="text"
            value={whitelistName}
            onChange={(event) => setWhitelistName(event.target.value)}
            placeholder="Name (e.g. GitHub MCP)"
            className="rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 text-sm text-white outline-none focus:border-brand-500/40"
          />
          <input
            type="url"
            value={whitelistUrl}
            onChange={(event) => setWhitelistUrl(event.target.value)}
            placeholder="https://api.githubcopilot.com/mcp/"
            className="rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 font-mono text-sm text-white outline-none focus:border-brand-500/40"
          />
          <button
            type="button"
            onClick={handleAddWhitelist}
            disabled={
              isAddingWhitelist || !whitelistName.trim() || !whitelistUrl.trim()
            }
            className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-brand-500 disabled:opacity-60"
          >
            {isAddingWhitelist ? "Adding..." : "Add to whitelist"}
          </button>
        </div>

        {addWhitelistError && (
          <p className="mt-4 text-sm text-red-300">{getErrorMessage(addWhitelistError)}</p>
        )}

        <div className="mt-6 space-y-3">
          {whitelist.length === 0 ? (
            <p className="text-sm text-slate-500">No whitelisted MCP servers yet.</p>
          ) : (
            whitelist.map((entry) => (
              <div
                key={entry.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/[0.06] bg-slate-900/40 px-4 py-3"
              >
                <div>
                  <p className="text-sm font-medium text-white">{entry.name}</p>
                  <p className="mt-1 font-mono text-xs text-slate-400">{entry.server_url}</p>
                </div>
                <button
                  type="button"
                  onClick={() => removeWhitelistEntry(entry.id)}
                  disabled={isRemovingWhitelist}
                  className="rounded-lg border border-white/[0.08] px-3 py-1.5 text-xs text-slate-300 transition hover:border-red-500/30 hover:text-red-300 disabled:opacity-60"
                >
                  Remove
                </button>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="panel rounded-2xl p-6 sm:p-8">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-white">Blocked MCP servers (blacklist)</h2>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Block specific MCP server URLs from ever being used, even if they appear on the
            platform allowlist.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-[1fr_auto]">
          <input
            type="url"
            value={blacklistUrl}
            onChange={(event) => setBlacklistUrl(event.target.value)}
            placeholder="https://untrusted-server.example/mcp"
            className="rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 font-mono text-sm text-white outline-none focus:border-brand-500/40"
          />
          <button
            type="button"
            onClick={handleAddBlacklist}
            disabled={isAddingBlacklist || !blacklistUrl.trim()}
            className="rounded-xl border border-red-500/30 bg-red-500/10 px-5 py-3 text-sm font-medium text-red-200 transition hover:bg-red-500/20 disabled:opacity-60"
          >
            {isAddingBlacklist ? "Adding..." : "Add to blacklist"}
          </button>
        </div>

        {addBlacklistError && (
          <p className="mt-4 text-sm text-red-300">{getErrorMessage(addBlacklistError)}</p>
        )}

        <div className="mt-6 space-y-3">
          {blacklist.length === 0 ? (
            <p className="text-sm text-slate-500">No blocked MCP servers yet.</p>
          ) : (
            blacklist.map((entry) => (
              <div
                key={entry.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-500/10 bg-red-500/5 px-4 py-3"
              >
                <p className="font-mono text-xs text-slate-300">{entry.server_url}</p>
                <button
                  type="button"
                  onClick={() => removeBlacklistEntry(entry.id)}
                  disabled={isRemovingBlacklist}
                  className="rounded-lg border border-white/[0.08] px-3 py-1.5 text-xs text-slate-300 transition hover:border-red-500/30 hover:text-red-300 disabled:opacity-60"
                >
                  Remove
                </button>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="panel rounded-2xl p-6 sm:p-8">
        <div className="mb-4">
          <h2 className="text-xl font-semibold text-white">Ask MCP</h2>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Ask a question and DevOps Open Agent will call tools on your MCP server to find the
            answer. Works well with GitHub MCP — for example, list open pull requests or inspect a
            repository.
          </p>
        </div>

        <label className="block text-sm font-medium text-slate-300">
          Your question
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={4}
            disabled={!mcpReady || isAsking}
            placeholder={
              mcpReady
                ? "e.g. List open pull requests in ideaweaver-ai/devops-testing"
                : "Save MCP settings and enable the integration before asking questions."
            }
            className="mt-2 w-full rounded-xl border border-white/[0.08] bg-slate-900/70 px-4 py-3 text-sm text-white outline-none focus:border-brand-500/40 disabled:opacity-60"
          />
        </label>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleAsk}
            disabled={!mcpReady || isAsking || !question.trim()}
            className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-brand-500 disabled:opacity-60"
          >
            {isAsking ? "Asking..." : "Ask question"}
          </button>
          {!mcpReady && (
            <p className="text-xs text-slate-500">
              Enable MCP and save a server URL to use this feature.
            </p>
          )}
        </div>

        {askResult && <McpAskResultPanel result={askResult} />}

        {askError && (
          <p className="mt-4 text-sm text-red-300">{getErrorMessage(askError)}</p>
        )}
      </section>

      <section className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6">
        <h2 className="text-lg font-semibold text-white">How it works</h2>
        <ul className="mt-4 space-y-3 text-sm text-slate-400">
          <li>
            Use <strong className="font-medium text-slate-300">Ask MCP</strong> to query your
            connected server directly with natural language.
          </li>
          <li>
            Pick from the <strong className="font-medium text-slate-300">official MCP server</strong>{" "}
            dropdown for GitHub, Linear, Sentry, and other supported remote servers.
          </li>
          <li>
            Add trusted servers to your <strong className="font-medium text-slate-300">whitelist</strong>.
            Once you have whitelist entries, only those servers can be selected as active.
          </li>
          <li>
            Use the <strong className="font-medium text-slate-300">blacklist</strong> to block
            specific MCP URLs from being used.
          </li>
          <li>
            Platform admins can restrict all users to specific URLs via{" "}
            <span className="font-mono text-slate-300">MCP_ALLOWED_SERVER_URLS</span> in{" "}
            <span className="font-mono text-slate-300">backend/.env</span>.
          </li>
          <li>
            When enabled for agents below, DevOps Open Agent also discovers MCP tools before AI
            diagnosis and includes them in investigation context.
          </li>
          {settings?.instance_server_configured && (
            <li>
              An instance-level MCP server is configured and will be used as a fallback when you
              have not set a personal URL.
            </li>
          )}
        </ul>
      </section>
    </div>
  );
}
