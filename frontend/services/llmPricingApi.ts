import { apiClient } from "@/services/api";
import type { LlmPricingTable, LlmPricingTableResponse } from "@/types/llmPricing";

export const llmPricingApi = {
  get: () => apiClient.get<LlmPricingTableResponse>("/api/v1/llm/pricing"),
  update: (table: LlmPricingTable) =>
    apiClient.put<LlmPricingTableResponse>("/api/v1/llm/pricing", { table }),
  reset: () => apiClient.post<LlmPricingTableResponse>("/api/v1/llm/pricing/reset"),
};
