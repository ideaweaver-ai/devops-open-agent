import { RequireAuth } from "@/components/auth/RequireAuth";
import { AppShell } from "@/components/layout/AppShell";
import { LlmPricingEditor } from "@/modules/usage/LlmPricingEditor";

export default function UsagePricingPage() {
  return (
    <RequireAuth>
      <AppShell>
        <LlmPricingEditor />
      </AppShell>
    </RequireAuth>
  );
}
