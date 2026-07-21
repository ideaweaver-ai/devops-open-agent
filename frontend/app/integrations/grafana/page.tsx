import { RequireAuth } from "@/components/auth/RequireAuth";
import { AppShell } from "@/components/layout/AppShell";
import { GrafanaIntegrationPage } from "@/modules/integrations/GrafanaIntegrationPage";

export default function GrafanaIntegrationRoute() {
  return (
    <RequireAuth>
      <AppShell>
        <GrafanaIntegrationPage />
      </AppShell>
    </RequireAuth>
  );
}
