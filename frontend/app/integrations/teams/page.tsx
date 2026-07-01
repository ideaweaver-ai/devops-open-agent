import { RequireAuth } from "@/components/auth/RequireAuth";
import { AppShell } from "@/components/layout/AppShell";
import { TeamsIntegrationPage } from "@/modules/integrations/TeamsIntegrationPage";

export default function TeamsIntegrationRoute() {
  return (
    <RequireAuth>
      <AppShell>
        <TeamsIntegrationPage />
      </AppShell>
    </RequireAuth>
  );
}
