"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { teamsIntegrationApi } from "@/services/teamsIntegrationApi";
import type { TeamsIntegrationSettings } from "@/types/teamsIntegration";

export function useTeamsIntegration() {
  const queryClient = useQueryClient();

  const settingsQuery = useQuery({
    queryKey: ["teams-integration"],
    queryFn: () => teamsIntegrationApi.getSettings(),
  });

  const saveMutation = useMutation({
    mutationFn: (settings: TeamsIntegrationSettings) =>
      teamsIntegrationApi.updateSettings(settings),
    onSuccess: (data) => {
      queryClient.setQueryData(["teams-integration"], data);
    },
  });

  const testMutation = useMutation({
    mutationFn: () => teamsIntegrationApi.sendTest(),
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
