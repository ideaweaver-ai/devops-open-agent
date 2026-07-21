import { apiClient } from "@/services/api";
import type {
  GrafanaIntegrationResponse,
  GrafanaIntegrationSettings,
  GrafanaTestResponse,
} from "@/types/grafanaIntegration";

export const grafanaIntegrationApi = {
  async getSettings(): Promise<GrafanaIntegrationResponse> {
    const response = await apiClient.get<GrafanaIntegrationResponse>(
      "/api/v1/integrations/grafana",
    );
    return response.data;
  },

  async updateSettings(
    settings: GrafanaIntegrationSettings,
  ): Promise<GrafanaIntegrationResponse> {
    const response = await apiClient.put<GrafanaIntegrationResponse>(
      "/api/v1/integrations/grafana",
      settings,
    );
    return response.data;
  },

  async sendTest(): Promise<GrafanaTestResponse> {
    const response = await apiClient.post<GrafanaTestResponse>(
      "/api/v1/integrations/grafana/test",
      undefined,
      { timeout: 45_000 },
    );
    return response.data;
  },
};
