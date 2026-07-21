import { apiClient } from "@/services/api";
import type {
  PrometheusIntegrationResponse,
  PrometheusIntegrationSettings,
  PrometheusTestResponse,
} from "@/types/prometheusIntegration";

export const prometheusIntegrationApi = {
  async getSettings(): Promise<PrometheusIntegrationResponse> {
    const response = await apiClient.get<PrometheusIntegrationResponse>(
      "/api/v1/integrations/prometheus",
    );
    return response.data;
  },

  async updateSettings(
    settings: PrometheusIntegrationSettings,
  ): Promise<PrometheusIntegrationResponse> {
    const response = await apiClient.put<PrometheusIntegrationResponse>(
      "/api/v1/integrations/prometheus",
      settings,
    );
    return response.data;
  },

  async sendTest(): Promise<PrometheusTestResponse> {
    const response = await apiClient.post<PrometheusTestResponse>(
      "/api/v1/integrations/prometheus/test",
      undefined,
      { timeout: 45_000 },
    );
    return response.data;
  },
};
