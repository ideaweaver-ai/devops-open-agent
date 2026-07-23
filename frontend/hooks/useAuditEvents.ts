import { useQuery } from "@tanstack/react-query";
import { auditApi } from "@/services/auditApi";

export function useAuditEvents(params?: { action?: string; limit?: number }) {
  return useQuery({
    queryKey: ["audit-events", params?.action ?? null, params?.limit ?? 100],
    queryFn: () => auditApi.listEvents(params),
  });
}
