import { apiClient } from "@/services/api";
import type {
  LlmBudgetResponse,
  LlmBudgetUpdateRequest,
  LlmUsageEventsResponse,
  LlmUsageSummaryResponse,
} from "@/types/llmUsage";

export const llmUsageApi = {
  getSummary: (params?: { from?: string; to?: string }) =>
    apiClient.get<LlmUsageSummaryResponse>("/api/v1/llm/usage/summary", {
      params,
    }),
  listEvents: (params?: { from?: string; to?: string; limit?: number }) =>
    apiClient.get<LlmUsageEventsResponse>("/api/v1/llm/usage/events", {
      params,
    }),
  getBudget: () => apiClient.get<LlmBudgetResponse>("/api/v1/llm/usage/budget"),
  updateBudget: (payload: LlmBudgetUpdateRequest) =>
    apiClient.put<LlmBudgetResponse>("/api/v1/llm/usage/budget", payload),
};
