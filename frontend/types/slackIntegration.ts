export type SlackDeliveryMethod = "webhook" | "channel";

export interface SlackIntegrationSettings {
  enabled: boolean;
  delivery_method: SlackDeliveryMethod;
  channel: string;
  webhook_url?: string | null;
  notify_kubernetes: boolean;
  notify_aws: boolean;
  notify_cloud_cost: boolean;
  notify_pr_reviewer: boolean;
  notify_performance: boolean;
  notify_security: boolean;
}

export interface SlackIntegrationResponse extends SlackIntegrationSettings {
  webhook_url_configured: boolean;
  webhook_url_preview: string | null;
  instance_bot_configured: boolean;
  instance_webhook_configured: boolean;
}

export interface SlackTestResponse {
  status: string;
  message: string;
}