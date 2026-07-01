import { apiClient } from "@/services/api";
import type {
  TeamsIntegrationResponse,
  TeamsIntegrationSettings,
  TeamsTestResponse,
} from "@/types/teamsIntegration";

export const teamsIntegrationApi = {
  async getSettings(): Promise<TeamsIntegrationResponse> {
    const response = await apiClient.get<TeamsIntegrationResponse>(
      "/api/v1/integrations/teams",
    );
    return response.data;
  },

  async updateSettings(
    settings: TeamsIntegrationSettings,
  ): Promise<TeamsIntegrationResponse> {
    const response = await apiClient.put<TeamsIntegrationResponse>(
      "/api/v1/integrations/teams",
      settings,
    );
    return response.data;
  },

  async sendTest(): Promise<TeamsTestResponse> {
    const response = await apiClient.post<TeamsTestResponse>(
      "/api/v1/integrations/teams/test",
    );
    return response.data;
  },
};
