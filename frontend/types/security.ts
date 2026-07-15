export type ScanType = "image" | "kubernetes";

export type ScanJobStatus = "queued" | "running" | "completed" | "failed";

export interface SecurityScanRequest {
  scan_type: ScanType;
  image_name?: string | null;
  namespace?: string | null;
  context?: string | null;
  include_ai?: boolean;
  severity_filter?: string[];
}

export interface VulnerabilityFinding {
  vulnerability_id: string;
  pkg_name: string;
  installed_version: string;
  fixed_version?: string | null;
  severity: string;
  title: string;
  description: string;
}

export interface MisconfigFinding {
  id: string;
  title: string;
  description: string;
  severity: string;
  resolution: string;
  resource?: string | null;
}

export interface ScanResult {
  scan_type: ScanType;
  target: string;
  vulnerabilities: VulnerabilityFinding[];
  misconfigurations: MisconfigFinding[];
  summary: Record<string, number>;
  ai_analysis?: string | null;
  llm_provider?: string | null;
  llm_error?: string | null;
}

export interface SecurityScanStartResponse {
  scan_id: string;
  status: ScanJobStatus;
  message: string;
}

export interface SecurityScanStatusResponse {
  scan_id: string;
  status: ScanJobStatus;
  current_step?: string | null;
  progress_percentage: number;
  error?: string | null;
}

export interface SecurityScanDetailResponse extends SecurityScanStatusResponse {
  agent_type: string;
  created_at?: string | null;
  updated_at?: string | null;
  result?: ScanResult | null;
}
