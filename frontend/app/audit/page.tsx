import { RequireAuth } from "@/components/auth/RequireAuth";
import { AppShell } from "@/components/layout/AppShell";
import { AuditLogPage } from "@/modules/audit/AuditLogPage";

export default function AuditPage() {
  return (
    <RequireAuth>
      <AppShell>
        <AuditLogPage />
      </AppShell>
    </RequireAuth>
  );
}
