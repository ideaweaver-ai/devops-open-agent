"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { pagerdutyIntegrationApi } from "@/services/pagerdutyIntegrationApi";
import type { PagerDutyIntegrationSettings } from "@/types/pagerdutyIntegration";

export function usePagerDutyIntegration() {
  const queryClient = useQueryClient();

  const settingsQuery = useQuery({
    queryKey: ["pagerduty-integration"],
    queryFn: () => pagerdutyIntegrationApi.getSettings(),
  });

  const saveMutation = useMutation({
    mutationFn: (settings: PagerDutyIntegrationSettings) =>
      pagerdutyIntegrationApi.updateSettings(settings),
    onSuccess: (data) => {
      queryClient.setQueryData(["pagerduty-integration"], data);
    },
  });

  const testMutation = useMutation({
    mutationFn: () => pagerdutyIntegrationApi.sendTest(),
  });

  return {
    settings: settingsQuery.data,
    isLoading: settingsQuery.isLoading,
    error: settingsQuery.error,
    saveSettings: saveMutation.mutateAsync,
    isSaving: saveMutation.isPending,
    saveError: saveMutation.error,
    sendTest: testMutation.mutateAsync,
    isTesting: testMutation.isPending,
    testResult: testMutation.data,
    testError: testMutation.error,
  };
}
