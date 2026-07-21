"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { grafanaIntegrationApi } from "@/services/grafanaIntegrationApi";
import type { GrafanaIntegrationSettings } from "@/types/grafanaIntegration";

export function useGrafanaIntegration() {
  const queryClient = useQueryClient();

  const settingsQuery = useQuery({
    queryKey: ["grafana-integration"],
    queryFn: () => grafanaIntegrationApi.getSettings(),
  });

  const saveMutation = useMutation({
    mutationFn: (settings: GrafanaIntegrationSettings) =>
      grafanaIntegrationApi.updateSettings(settings),
    onSuccess: (data) => {
      queryClient.setQueryData(["grafana-integration"], data);
    },
  });

  const testMutation = useMutation({
    mutationFn: () => grafanaIntegrationApi.sendTest(),
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
