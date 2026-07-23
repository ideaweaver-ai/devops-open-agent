"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { llmUsageApi } from "@/services/llmUsageApi";

export function useLlmUsageSummary(enabled = true, range?: { from?: string; to?: string }) {
  return useQuery({
    queryKey: ["llm-usage", "summary", range?.from ?? "default", range?.to ?? "default"],
    queryFn: async () => {
      const { data } = await llmUsageApi.getSummary(range);
      return data;
    },
    enabled,
  });
}

export function useLlmUsageEvents(enabled = true, range?: { from?: string; to?: string }) {
  return useQuery({
    queryKey: ["llm-usage", "events", range?.from ?? "default", range?.to ?? "default"],
    queryFn: async () => {
      const { data } = await llmUsageApi.listEvents({ ...range, limit: 100 });
      return data;
    },
    enabled,
  });
}

export function useLlmBudget() {
  return useQuery({
    queryKey: ["llm-usage", "budget"],
    queryFn: async () => {
      const { data } = await llmUsageApi.getBudget();
      return data;
    },
  });
}

export function useUpdateLlmBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (llm_daily_budget_usd: number | null) => {
      const { data } = await llmUsageApi.updateBudget({ llm_daily_budget_usd });
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["llm-usage", "budget"] });
    },
  });
}
