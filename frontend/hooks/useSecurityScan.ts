"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { securityApi } from "@/services/securityApi";
import type { SecurityScanRequest } from "@/types/security";

export function useStartSecurityScan() {
  return useMutation({
    mutationFn: (request: SecurityScanRequest) => securityApi.startScan(request),
  });
}

export function useSecurityScanStatus(scanId: string | null, enabled = true) {
  return useQuery({
    queryKey: ["security", "status", scanId],
    queryFn: () => securityApi.getScanStatus(scanId!),
    enabled: Boolean(scanId) && enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status || status === "completed" || status === "failed") {
        return false;
      }
      return 2_000;
    },
  });
}

export function useSecurityScanDetail(scanId: string | null, enabled = true) {
  return useQuery({
    queryKey: ["security", "detail", scanId],
    queryFn: () => securityApi.getScanDetail(scanId!),
    enabled: Boolean(scanId) && enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status || status === "completed" || status === "failed") {
        return false;
      }
      return 2_000;
    },
  });
}
