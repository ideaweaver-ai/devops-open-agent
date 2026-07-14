export type HostDebugStatus =
  | "pending"
  | "collecting"
  | "analyzing"
  | "completed"
  | "failed";

export type PerformanceJobStatus = "queued" | "running" | "completed" | "failed";

export interface PerformanceDebugRequest {
  hosts: string[];
}

export interface PerformanceDebugStartResponse {
  debug_id: string;
  status: PerformanceJobStatus;
  message: string;
  host_count: number;
}

export interface HostDebugResult {
  host: string;
  status: HostDebugStatus;
  message?: string | null;
  evidence?: string | null;
  analysis?: string | null;
  summary?: string | null;
  severity?: string | null;
  error?: string | null;
}

export interface PerformanceDebugStatus {
  debug_id: string;
  status: PerformanceJobStatus;
  current_step?: string | null;
  progress_percentage: number;
  hosts: HostDebugResult[];
  error?: string | null;
}

export interface PerformanceDebugDetail extends PerformanceDebugStatus {
  agent_type: string;
  created_at?: string | null;
  updated_at?: string | null;
  overall_summary?: string | null;
}
