"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { performanceApi } from "@/services/performanceApi";
import type { PerformanceDebugRequest } from "@/types/performance";

export function usePerformanceDebugHistory() {
  return useQuery({
    queryKey: ["performance", "history"],
    queryFn: () => performanceApi.listJobs(),
    refetchInterval: 10_000,
  });
}

export function useStartPerformanceDebug() {
  return useMutation({
    mutationFn: (request: PerformanceDebugRequest) => performanceApi.startDebug(request),
  });
}

export function usePerformanceDebugStatus(debugId: string | null, enabled = true) {
  return useQuery({
    queryKey: ["performance", "status", debugId],
    queryFn: () => performanceApi.getStatus(debugId!),
    enabled: Boolean(debugId) && enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status || status === "completed" || status === "failed") {
        return false;
      }
      return 2_000;
    },
  });
}

export function usePerformanceDebugDetail(debugId: string | null, enabled = true) {
  return useQuery({
    queryKey: ["performance", "detail", debugId],
    queryFn: () => performanceApi.getDetail(debugId!),
    enabled: Boolean(debugId) && enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status || status === "completed" || status === "failed") {
        return false;
      }
      return 2_000;
    },
  });
}
