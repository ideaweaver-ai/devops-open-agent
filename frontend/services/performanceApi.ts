import { apiClient } from "@/services/api";
import type {
  PerformanceDebugDetail,
  PerformanceDebugRequest,
  PerformanceDebugStartResponse,
  PerformanceDebugStatus,
} from "@/types/performance";

export const performanceApi = {
  async startDebug(request: PerformanceDebugRequest): Promise<PerformanceDebugStartResponse> {
    const response = await apiClient.post<PerformanceDebugStartResponse>(
      "/api/v1/performance/debug",
      request,
      { timeout: 30_000 },
    );
    return response.data;
  },

  async getStatus(debugId: string): Promise<PerformanceDebugStatus> {
    const response = await apiClient.get<PerformanceDebugStatus>(
      `/api/v1/performance/debug/${debugId}/status`,
    );
    return response.data;
  },

  async getDetail(debugId: string): Promise<PerformanceDebugDetail> {
    const response = await apiClient.get<PerformanceDebugDetail>(
      `/api/v1/performance/debug/${debugId}`,
    );
    return response.data;
  },
};
