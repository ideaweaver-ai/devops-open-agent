import { RequireAuth } from "@/components/auth/RequireAuth";
import { AppShell } from "@/components/layout/AppShell";
import { PagerDutyIntegrationPage } from "@/modules/integrations/PagerDutyIntegrationPage";

export default function PagerDutyIntegrationRoute() {
  return (
    <RequireAuth>
      <AppShell>
        <PagerDutyIntegrationPage />
      </AppShell>
    </RequireAuth>
  );
}
