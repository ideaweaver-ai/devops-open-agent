"use client";

import { Suspense } from "react";
import { SecurityScanningPage } from "@/modules/security/SecurityScanningPage";

export default function SecurityRoute() {
  return (
    <Suspense>
      <SecurityScanningPage />
    </Suspense>
  );
}
