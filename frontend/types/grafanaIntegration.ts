export interface GrafanaIntegrationSettings {
  enabled: boolean;
  url: string;
  api_token?: string | null;
  use_kubernetes: boolean;
}

export interface GrafanaIntegrationResponse {
  enabled: boolean;
  url: string;
  api_token_configured: boolean;
  api_token_preview: string | null;
  use_kubernetes: boolean;
  instance_url_configured: boolean;
}

export interface GrafanaTestResponse {
  status: string;
  message: string;
  version: string | null;
  org_name: string | null;
}
