import { RequireAuth } from "@/components/auth/RequireAuth";
import { AppShell } from "@/components/layout/AppShell";
import { AwsIntegrationPage } from "@/modules/integrations/AwsIntegrationPage";

export default function AwsIntegrationRoute() {
  return (
    <RequireAuth>
      <AppShell>
        <AwsIntegrationPage />
      </AppShell>
    </RequireAuth>
  );
}
