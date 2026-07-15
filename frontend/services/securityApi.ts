import { apiClient } from "@/services/api";
import type {
  SecurityScanDetailResponse,
  SecurityScanRequest,
  SecurityScanStartResponse,
  SecurityScanStatusResponse,
} from "@/types/security";

export const securityApi = {
  async startScan(request: SecurityScanRequest): Promise<SecurityScanStartResponse> {
    const response = await apiClient.post<SecurityScanStartResponse>(
      "/api/v1/security/scan",
      request,
      { timeout: 30_000 },
    );
    return response.data;
  },

  async getScanStatus(scanId: string): Promise<SecurityScanStatusResponse> {
    const response = await apiClient.get<SecurityScanStatusResponse>(
      `/api/v1/security/scan/${scanId}/status`,
    );
    return response.data;
  },

  async getScanDetail(scanId: string): Promise<SecurityScanDetailResponse> {
    const response = await apiClient.get<SecurityScanDetailResponse>(
      `/api/v1/security/scan/${scanId}`,
    );
    return response.data;
  },
};
