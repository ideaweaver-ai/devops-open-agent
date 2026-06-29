export interface PagerDutyIntegrationSettings {
  enabled: boolean;
  routing_key?: string | null;
  notification_cooldown_minutes: number;
  notify_kubernetes: boolean;
  notify_aws: boolean;
  notify_cloud_cost: boolean;
  notify_pr_reviewer: boolean;
}

export interface PagerDutyIntegrationResponse {
  enabled: boolean;
  routing_key_configured: boolean;
  routing_key_preview: string | null;
  notification_cooldown_minutes: number;
  default_cooldown_minutes: number;
  notify_kubernetes: boolean;
  notify_aws: boolean;
  notify_cloud_cost: boolean;
  notify_pr_reviewer: boolean;
  instance_routing_key_configured: boolean;
}

export interface PagerDutyTestResponse {
  status: string;
  message: string;
}
