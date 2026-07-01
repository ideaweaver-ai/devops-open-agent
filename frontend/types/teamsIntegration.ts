export interface TeamsIntegrationSettings {
  enabled: boolean;
  webhook_url?: string | null;
  notify_kubernetes: boolean;
  notify_aws: boolean;
  notify_cloud_cost: boolean;
  notify_pr_reviewer: boolean;
}

export interface TeamsIntegrationResponse {
  enabled: boolean;
  webhook_url_configured: boolean;
  webhook_url_preview: string | null;
  notify_kubernetes: boolean;
  notify_aws: boolean;
  notify_cloud_cost: boolean;
  notify_pr_reviewer: boolean;
  instance_webhook_configured: boolean;
}

export interface TeamsTestResponse {
  status: string;
  message: string;
}
