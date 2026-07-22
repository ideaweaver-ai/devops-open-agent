"use client";

import type { ClusterItem } from "@/types/system";
import { ClusterSelector } from "@/components/ClusterSelector";

const JUDGE_PROVIDERS = [
  { value: "", label: "Same as primary (default)" },
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "gemini", label: "Google Gemini" },
  { value: "openrouter", label: "OpenRouter" },
  { value: "bedrock", label: "AWS Bedrock" },
  { value: "ollama", label: "Ollama (local)" },
] as const;

const JUDGE_MODEL_HINTS: Record<string, string> = {
  openai: "e.g. gpt-4o, gpt-4o-mini",
  anthropic: "e.g. claude-sonnet-4-20250514",
  gemini: "e.g. gemini-2.0-flash",
  openrouter: "e.g. openai/gpt-4o-mini",
  bedrock: "e.g. anthropic.claude-3-5-sonnet-20241022-v2:0",
  ollama: "e.g. llama3.1, gemma3",
};

interface InvestigationFormProps {
  clusters: ClusterItem[];
  clusterId: string;
  onClusterChange: (clusterId: string) => void;
  onInvestigate: () => void;
  isLoading: boolean;
  disabled?: boolean;
  clustersLoading?: boolean;
  clustersError?: string | null;
  includeRag?: boolean;
  onIncludeRagChange?: (value: boolean) => void;
  ragAvailable?: boolean;
  includeJudge?: boolean;
  onIncludeJudgeChange?: (value: boolean) => void;
  judgeProvider?: string;
  onJudgeProviderChange?: (value: string) => void;
  judgeModel?: string;
  onJudgeModelChange?: (value: string) => void;
}

export function InvestigationForm({
  clusters,
  clusterId,
  onClusterChange,
  onInvestigate,
  isLoading,
  disabled = false,
  clustersLoading = false,
  clustersError = null,
  includeRag = false,
  onIncludeRagChange,
  ragAvailable = false,
  includeJudge = false,
  onIncludeJudgeChange,
  judgeProvider = "",
  onJudgeProviderChange,
  judgeModel = "",
  onJudgeModelChange,
}: InvestigationFormProps) {
  return (
    <div className="panel-accent p-6">
      <div className="mb-5 flex items-center gap-3 border-b border-slate-200 pb-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-brand-200 bg-brand-50">
          <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4 text-brand-700" aria-hidden>
            <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.5" />
            <path
              d="M12 2v3M12 19v3M2 12h3M19 12h3"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        </div>
        <div>
          <h2 className="panel-title">Start Investigation</h2>
          <p className="text-xs text-slate-600">Select a cluster context to analyze</p>
        </div>
      </div>

      <div className="mb-5">
        <ClusterSelector
          clusters={clusters}
          clusterId={clusterId}
          onClusterChange={onClusterChange}
          disabled={disabled || isLoading}
          loading={clustersLoading}
          error={clustersError}
        />
      </div>

      {ragAvailable && (
        <label className="mb-5 flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
          <input
            type="checkbox"
            checked={includeRag}
            disabled={disabled || isLoading}
            onChange={(event) => onIncludeRagChange?.(event.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
          />
          <span>
            <span className="block text-sm font-medium text-slate-900">
              Include past investigations (RAG)
            </span>
            <span className="mt-0.5 block text-xs text-slate-600">
              Retrieve similar prior investigations from Qdrant and factor them into the AI
              analysis.
            </span>
          </span>
        </label>
      )}

      <div className="mb-5 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
        <label className="flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            checked={includeJudge}
            disabled={disabled || isLoading}
            onChange={(event) => onIncludeJudgeChange?.(event.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
          />
          <span>
            <span className="block text-sm font-medium text-slate-900">
              Verify with a second AI (LLM-as-a-Judge)
            </span>
            <span className="mt-0.5 block text-xs text-slate-600">
              A secondary AI reviews the diagnosis for factual consistency, evidence
              grounding, and command safety.
            </span>
          </span>
        </label>

        {includeJudge && (
          <div className="mt-3 grid gap-3 border-t border-slate-200 pt-3 sm:grid-cols-2">
            <div>
              <label htmlFor="judge-provider" className="mb-1 block text-xs font-medium text-slate-700">
                Judge Provider
              </label>
              <select
                id="judge-provider"
                value={judgeProvider}
                disabled={disabled || isLoading}
                onChange={(e) => onJudgeProviderChange?.(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              >
                {JUDGE_PROVIDERS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="judge-model" className="mb-1 block text-xs font-medium text-slate-700">
                Judge Model
              </label>
              <input
                id="judge-model"
                type="text"
                value={judgeModel}
                disabled={disabled || isLoading}
                onChange={(e) => onJudgeModelChange?.(e.target.value)}
                placeholder={
                  judgeProvider
                    ? JUDGE_MODEL_HINTS[judgeProvider] ?? "Model name"
                    : "Leave empty for default"
                }
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              />
            </div>
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={onInvestigate}
        disabled={disabled || isLoading || !clusterId}
        className="btn-primary max-w-xs"
      >
        {isLoading ? (
          <span className="flex items-center gap-2">
            <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            Investigating...
          </span>
        ) : (
          "Investigate Cluster"
        )}
      </button>
    </div>
  );
}
