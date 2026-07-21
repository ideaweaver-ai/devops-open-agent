import { RequireAuth } from "@/components/auth/RequireAuth";
import { AppShell } from "@/components/layout/AppShell";
import { PrometheusIntegrationPage } from "@/modules/integrations/PrometheusIntegrationPage";

export default function PrometheusIntegrationRoute() {
  return (
    <RequireAuth>
      <AppShell>
        <PrometheusIntegrationPage />
      </AppShell>
    </RequireAuth>
  );
}
