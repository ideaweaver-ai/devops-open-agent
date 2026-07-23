import { RequireAuth } from "@/components/auth/RequireAuth";
import { AppShell } from "@/components/layout/AppShell";
import { LlmUsageDashboard } from "@/modules/usage/LlmUsageDashboard";

export default function UsagePage() {
  return (
    <RequireAuth>
      <AppShell>
        <LlmUsageDashboard />
      </AppShell>
    </RequireAuth>
  );
}
