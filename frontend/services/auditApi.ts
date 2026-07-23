import { apiClient } from "@/services/api";
import type { AuditEventsResponse } from "@/types/audit";

export const auditApi = {
  async listEvents(params?: { action?: string; limit?: number }): Promise<AuditEventsResponse> {
    const { data } = await apiClient.get<AuditEventsResponse>("/api/v1/audit/events", {
      params,
    });
    return data;
  },
};
