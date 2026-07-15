"use client";

import { Suspense } from "react";
import { PerformanceDebuggingPage } from "@/modules/performance/PerformanceDebuggingPage";

export default function PerformanceRoute() {
  return (
    <Suspense>
      <PerformanceDebuggingPage />
    </Suspense>
  );
}
