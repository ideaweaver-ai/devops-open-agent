"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { llmPricingApi } from "@/services/llmPricingApi";
import type { LlmPricingTable } from "@/types/llmPricing";

export function useLlmPricing() {
  return useQuery({
    queryKey: ["llm-pricing"],
    queryFn: async () => {
      const { data } = await llmPricingApi.get();
      return data;
    },
  });
}

export function useSaveLlmPricing() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (table: LlmPricingTable) => {
      const { data } = await llmPricingApi.update(table);
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["llm-pricing"] });
    },
  });
}

export function useResetLlmPricing() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await llmPricingApi.reset();
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["llm-pricing"] });
    },
  });
}
