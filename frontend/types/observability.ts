export interface IntegrationStatus {
  enabled: boolean;
  error?: string | null;
}

export interface ObservabilityFinding {
  source: "prometheus" | "grafana" | string;
  title: string;
  severity?: string | null;
  detail: string;
  query?: string | null;
  timestamp?: string | null;
}

export interface ObservabilityResult {
  enabled: boolean;
  prometheus?: IntegrationStatus;
  grafana?: IntegrationStatus;
  loki?: IntegrationStatus;
  opentelemetry?: IntegrationStatus;
  findings: ObservabilityFinding[];
  summary?: string | null;
}
