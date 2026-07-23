export interface AuditEvent {
  id: string;
  created_at: string;
  actor_user_id?: string | null;
  actor_email?: string | null;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface AuditEventsResponse {
  events: AuditEvent[];
}
