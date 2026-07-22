"use client";

export function formatLlmProviderLabel(provider: string | null | undefined): string | null {
  if (!provider) {
    return null;
  }

  const labels: Record<string, string> = {
    openai: "OpenAI",
    ollama: "Ollama",
    anthropic: "Anthropic",
    openrouter: "OpenRouter",
    gemini: "Google Gemini",
    bedrock: "AWS Bedrock",
  };

  return labels[provider.toLowerCase()] ?? provider;
}

function providerStyles(provider: string): string {
  switch (provider.toLowerCase()) {
    case "openai":
      return "border-emerald-500/25 bg-emerald-500/10 text-emerald-200";
    case "ollama":
      return "border-violet-500/25 bg-violet-500/10 text-violet-200";
    case "anthropic":
      return "border-orange-500/25 bg-orange-500/10 text-orange-200";
    case "openrouter":
      return "border-sky-500/25 bg-sky-500/10 text-sky-200";
    case "gemini":
      return "border-blue-500/25 bg-blue-500/10 text-blue-200";
    case "bedrock":
      return "border-amber-500/25 bg-amber-500/10 text-amber-200";
    default:
      return "border-slate-500/25 bg-slate-500/10 text-slate-200";
  }
}

export function LlmProviderBadge({ provider }: { provider?: string | null }) {
  const label = formatLlmProviderLabel(provider);

  if (!label || !provider) {
    return null;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${providerStyles(provider)}`}
      title={`AI diagnosis powered by ${label}`}
    >
      <span className="text-[10px] font-semibold uppercase tracking-wide opacity-80">AI</span>
      <span className="opacity-60">·</span>
      <span>{label}</span>
    </span>
  );
}
