export interface McpIntegrationSettings {
  enabled: boolean;
  server_url: string;
  api_key?: string | null;
  use_kubernetes: boolean;
  use_aws: boolean;
  use_cloud_cost: boolean;
  use_pr_reviewer: boolean;
  use_performance: boolean;
  use_security: boolean;
}

export interface McpWhitelistEntry {
  id: string;
  name: string;
  server_url: string;
}

export interface McpBlacklistEntry {
  id: string;
  server_url: string;
}

export interface McpWhitelistCreate {
  name: string;
  server_url: string;
}

export interface McpBlacklistCreate {
  server_url: string;
}

export interface McpOfficialServer {
  id: string;
  name: string;
  server_url: string;
  description: string;
  docs_url: string;
  auth_hint: string;
  category: string;
}

export interface McpIntegrationResponse {
  enabled: boolean;
  server_url: string;
  api_key_configured: boolean;
  api_key_preview: string | null;
  use_kubernetes: boolean;
  use_aws: boolean;
  use_cloud_cost: boolean;
  use_pr_reviewer: boolean;
  use_performance: boolean;
  use_security: boolean;
  instance_server_configured: boolean;
  instance_url_restrictions_enabled: boolean;
  instance_allowed_urls: string[];
  official_servers: McpOfficialServer[];
  whitelist: McpWhitelistEntry[];
  blacklist: McpBlacklistEntry[];
}

export interface McpTestResponse {
  status: string;
  message: string;
  tool_count: number;
  resource_count: number;
  tools: string[];
}

export interface McpToolCallRecord {
  tool_name: string;
  arguments: Record<string, unknown>;
  result_summary: string;
}

export interface McpAskRequest {
  question: string;
}

export interface McpAskResponse {
  answer: string;
  tools_used: McpToolCallRecord[];
}
