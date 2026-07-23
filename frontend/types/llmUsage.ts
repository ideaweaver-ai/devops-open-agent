export interface LlmUsageCall {
  provider: string;
  model: string;
  call_kind: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_usd?: number | null;
}

export interface LlmUsageSummary {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_usd?: number | null;
  call_count: number;
  calls?: LlmUsageCall[];
}

export interface LlmUsageTotals {
  call_count: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_usd: number;
}

export interface LlmUsageBucket {
  key: string;
  call_count: number;
  total_tokens: number;
  estimated_usd: number;
}

export interface LlmUsageSummaryResponse {
  from: string;
  to: string;
  totals: LlmUsageTotals;
  by_day: LlmUsageBucket[];
  by_agent: LlmUsageBucket[];
  by_provider: LlmUsageBucket[];
  by_call_kind: LlmUsageBucket[];
}

export interface LlmUsageEvent {
  id: string;
  created_at: string;
  user_id?: string | null;
  scope_type: string;
  scope_id: string;
  agent_type?: string | null;
  provider: string;
  model: string;
  call_kind: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_usd?: number | null;
}

export interface LlmUsageEventsResponse {
  events: LlmUsageEvent[];
}

export interface LlmBudgetResponse {
  llm_daily_budget_usd: number | null;
  today_estimated_usd: number;
  budget_alert_date?: string | null;
}

export interface LlmBudgetUpdateRequest {
  llm_daily_budget_usd: number | null;
}
