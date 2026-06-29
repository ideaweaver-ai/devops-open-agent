import { apiClient } from "@/services/api";
import type {
  PagerDutyIntegrationResponse,
  PagerDutyIntegrationSettings,
  PagerDutyTestResponse,
} from "@/types/pagerdutyIntegration";

export const pagerdutyIntegrationApi = {
  async getSettings(): Promise<PagerDutyIntegrationResponse> {
    const response = await apiClient.get<PagerDutyIntegrationResponse>(
      "/api/v1/integrations/pagerduty",
    );
    return response.data;
  },

  async updateSettings(
    settings: PagerDutyIntegrationSettings,
  ): Promise<PagerDutyIntegrationResponse> {
    const response = await apiClient.put<PagerDutyIntegrationResponse>(
      "/api/v1/integrations/pagerduty",
      settings,
    );
    return response.data;
  },

  async sendTest(): Promise<PagerDutyTestResponse> {
    const response = await apiClient.post<PagerDutyTestResponse>(
      "/api/v1/integrations/pagerduty/test",
    );
    return response.data;
  },
};
