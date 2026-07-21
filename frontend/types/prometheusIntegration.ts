export interface PrometheusIntegrationSettings {
  enabled: boolean;
  url: string;
  bearer_token?: string | null;
  basic_auth_user?: string | null;
  basic_auth_password?: string | null;
  use_kubernetes: boolean;
}

export interface PrometheusIntegrationResponse {
  enabled: boolean;
  url: string;
  bearer_token_configured: boolean;
  bearer_token_preview: string | null;
  basic_auth_user: string;
  basic_auth_password_configured: boolean;
  use_kubernetes: boolean;
  instance_url_configured: boolean;
}

export interface PrometheusTestResponse {
  status: string;
  message: string;
  version: string | null;
}
