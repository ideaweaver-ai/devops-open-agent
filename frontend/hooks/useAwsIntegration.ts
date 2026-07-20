"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { awsIntegrationApi } from "@/services/awsIntegrationApi";
import type { AwsIntegrationSettings, AwsTestRequest } from "@/types/awsIntegration";

export function useAwsIntegration() {
  const queryClient = useQueryClient();

  const settingsQuery = useQuery({
    queryKey: ["aws-integration"],
    queryFn: () => awsIntegrationApi.getSettings(),
  });

  const saveMutation = useMutation({
    mutationFn: (settings: AwsIntegrationSettings) =>
      awsIntegrationApi.updateSettings(settings),
    onSuccess: (data) => {
      queryClient.setQueryData(["aws-integration"], data);
      void queryClient.invalidateQueries({ queryKey: ["aws", "accounts"] });
    },
  });

  const testMutation = useMutation({
    mutationFn: (payload?: AwsTestRequest) => awsIntegrationApi.sendTest(payload),
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
