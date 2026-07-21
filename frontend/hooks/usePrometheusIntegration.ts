"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { prometheusIntegrationApi } from "@/services/prometheusIntegrationApi";
import type { PrometheusIntegrationSettings } from "@/types/prometheusIntegration";

export function usePrometheusIntegration() {
  const queryClient = useQueryClient();

  const settingsQuery = useQuery({
    queryKey: ["prometheus-integration"],
    queryFn: () => prometheusIntegrationApi.getSettings(),
  });

  const saveMutation = useMutation({
    mutationFn: (settings: PrometheusIntegrationSettings) =>
      prometheusIntegrationApi.updateSettings(settings),
    onSuccess: (data) => {
      queryClient.setQueryData(["prometheus-integration"], data);
    },
  });

  const testMutation = useMutation({
    mutationFn: () => prometheusIntegrationApi.sendTest(),
  });

  return {
    settings: settingsQuery.data,
    isLoading: settingsQuery.isLoading,
    saveSettings: saveMutation.mutateAsync,
    isSaving: saveMutation.isPending,
    saveError: saveMutation.error,
    sendTest: testMutation.mutateAsync,
    isTesting: testMutation.isPending,
    testResult: testMutation.data,
    testError: testMutation.error,
  };
}
