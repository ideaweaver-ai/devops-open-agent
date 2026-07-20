import { apiClient } from "@/services/api";
import type {
  AwsIntegrationResponse,
  AwsIntegrationSettings,
  AwsTestRequest,
  AwsTestResponse,
} from "@/types/awsIntegration";

export const awsIntegrationApi = {
  async getSettings(): Promise<AwsIntegrationResponse> {
    const response = await apiClient.get<AwsIntegrationResponse>("/api/v1/integrations/aws");
    return response.data;
  },

  async updateSettings(
    settings: AwsIntegrationSettings,
  ): Promise<AwsIntegrationResponse> {
    const response = await apiClient.put<AwsIntegrationResponse>(
      "/api/v1/integrations/aws",
      settings,
    );
    return response.data;
  },

  async sendTest(payload?: AwsTestRequest): Promise<AwsTestResponse> {
    const response = await apiClient.post<AwsTestResponse>(
      "/api/v1/integrations/aws/test",
      payload ?? {},
      { timeout: 45_000 },
    );
    return response.data;
  },
};
