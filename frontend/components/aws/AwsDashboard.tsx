"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { AppShell } from "@/components/layout/AppShell";
import { DiagnosisCard } from "@/components/DiagnosisCard";
import { InvestigationProgress } from "@/components/InvestigationProgress";
import { AwsInvestigationForm } from "@/components/aws/AwsInvestigationForm";
import { AwsInvestigationResults } from "@/components/aws/AwsInvestigationResults";
import {
  useAwsAccounts,
  useAwsRegions,
} from "@/hooks/useAwsInvestigation";
import { useInvestigation } from "@/hooks/useInvestigation";
import { useQdrantIntegration } from "@/hooks/useQdrantIntegration";
import { usePrometheusIntegration } from "@/hooks/usePrometheusIntegration";
import { useGrafanaIntegration } from "@/hooks/useGrafanaIntegration";
import {
  useInvestigationResult,
  useInvestigationStatus,
} from "@/hooks/useInvestigationStatus";
import type { AwsIssueType, CloudWatchWindow } from "@/types/aws";
import { AWS_INVESTIGATION_STEPS } from "@/types/investigation";
import type { AwsInvestigationResponse } from "@/types/aws";

const TERMINAL_STATUSES = new Set(["success", "partial_success", "completed", "failed"]);

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      return "Unable to reach the backend API. Start the backend and try again.";
    }
    const detail = error.response.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    return `Request failed with status ${error.response.status}.`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "An unexpected error occurred.";
}

export function AwsDashboard() {
  const [accountId, setAccountId] = useState("");
  const [region, setRegion] = useState("");
  const [cloudwatchWindow, setCloudwatchWindow] = useState<CloudWatchWindow>("24h");
  const [issueType, setIssueType] = useState<AwsIssueType>("full_scan");
  const [query, setQuery] = useState("");
  const [activeInvestigationId, setActiveInvestigationId] = useState<string | null>(null);
  const [userError, setUserError] = useState<string | null>(null);
  const [includeRag, setIncludeRag] = useState(false);

  const accountsQuery = useAwsAccounts();
  const regionsQuery = useAwsRegions(accountId, region || undefined, Boolean(accountId));
  const { startInvestigation, isStarting, startError, reset } = useInvestigation();
  const { settings: qdrantSettings } = useQdrantIntegration();
  const { settings: prometheusSettings, isLoading: prometheusLoading } =
    usePrometheusIntegration();
  const { settings: grafanaSettings, isLoading: grafanaLoading } =
    useGrafanaIntegration();
  const ragAvailable = Boolean(
    (qdrantSettings?.enabled && qdrantSettings?.use_aws) ||
      qdrantSettings?.instance_url_configured,
  );
  const prometheusEnabled = Boolean(
    prometheusSettings?.enabled &&
      (prometheusSettings.url?.trim() || prometheusSettings.instance_url_configured),
  );
  const grafanaEnabled = Boolean(
    grafanaSettings?.enabled &&
      (grafanaSettings.url?.trim() || grafanaSettings.instance_url_configured),
  );
  const statusQuery = useInvestigationStatus(activeInvestigationId);
  const status = statusQuery.data?.status;
  const isTerminal = Boolean(status && TERMINAL_STATUSES.has(status));
  const resultQuery = useInvestigationResult(activeInvestigationId, isTerminal);

  useEffect(() => {
    const accounts = accountsQuery.data?.accounts ?? [];
    if (accounts.length > 0 && !accountId) {
      setAccountId(accounts[0].account_id);
    }
  }, [accountsQuery.data, accountId]);

  useEffect(() => {
    const regions = regionsQuery.data?.regions ?? [];
    if (regions.length > 0 && !region) {
      setRegion(regions[0].region);
    }
  }, [regionsQuery.data, region]);

  useEffect(() => {
    setRegion("");
    setActiveInvestigationId(null);
  }, [accountId]);

  useEffect(() => {
    if (startError) {
      setUserError(getErrorMessage(startError));
    }
  }, [startError]);

  useEffect(() => {
    if (statusQuery.data?.error && statusQuery.data.status === "failed") {
      setUserError(statusQuery.data.error);
    }
  }, [statusQuery.data?.error, statusQuery.data?.status]);

  const handleInvestigate = async () => {
    if (!accountId || !region) {
      setUserError("Select an account and region before starting an investigation.");
      return;
    }

    setUserError(null);
    reset();

    try {
      const response = await startInvestigation({
        agent_type: "aws",
        account_id: accountId,
        region,
        cloudwatch_window: cloudwatchWindow,
        issue_type: issueType,
        query: query.trim() || null,
        include_ai: true,
        include_rag: ragAvailable && includeRag,
      });
      setActiveInvestigationId(response.investigation_id);
    } catch (error) {
      setUserError(getErrorMessage(error));
    }
  };

  const diagnosis =
    resultQuery.data?.diagnosis ?? resultQuery.data?.aws_result?.diagnosis ?? null;
  const resultStatus = resultQuery.data?.status ?? status;
  const awsResult = (resultQuery.data?.aws_result ?? null) as AwsInvestigationResponse | null;

  const accountsError = accountsQuery.isError
    ? getErrorMessage(accountsQuery.error)
    : null;
  const regionsError = regionsQuery.isError ? getErrorMessage(regionsQuery.error) : null;

  return (
    <AppShell>
      {userError && (
        <div className="alert-error mb-6 flex gap-3">
          <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-500/20 text-xs text-red-300">
            !
          </span>
          <div>{userError}</div>
        </div>
      )}

      <div className="space-y-6">
        <AwsInvestigationForm
          accounts={accountsQuery.data?.accounts ?? []}
          accountId={accountId}
          onAccountChange={setAccountId}
          regions={regionsQuery.data?.regions ?? []}
          region={region}
          onRegionChange={setRegion}
          cloudwatchWindow={cloudwatchWindow}
          onCloudwatchWindowChange={setCloudwatchWindow}
          issueType={issueType}
          onIssueTypeChange={setIssueType}
          query={query}
          onQueryChange={setQuery}
          onInvestigate={handleInvestigate}
          isLoading={isStarting || status === "running"}
          disabled={status === "running"}
          accountsLoading={accountsQuery.isLoading}
          accountsError={accountsError}
          regionsLoading={regionsQuery.isLoading}
          regionsError={regionsError}
          includeRag={includeRag}
          onIncludeRagChange={setIncludeRag}
          ragAvailable={ragAvailable}
          prometheusEnabled={prometheusEnabled}
          grafanaEnabled={grafanaEnabled}
          observabilityLoading={prometheusLoading || grafanaLoading}
        />

        {activeInvestigationId && statusQuery.data && (
          <InvestigationProgress
            currentStep={statusQuery.data.current_step}
            progressPercentage={statusQuery.data.progress_percentage}
            status={statusQuery.data.status}
            steps={AWS_INVESTIGATION_STEPS}
            title="Investigating AWS Infrastructure..."
          />
        )}

        {resultQuery.isLoading && isTerminal && (
          <div className="alert-loading flex items-center gap-3">
            <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-orange-500/30 border-t-orange-400" />
            Loading investigation results...
          </div>
        )}

        {resultQuery.isError && (
          <div className="alert-error">
            Failed to load investigation result. {getErrorMessage(resultQuery.error)}
          </div>
        )}

        {isTerminal && awsResult && (
          <>
            <DiagnosisCard
              diagnosis={diagnosis}
              status={resultStatus}
              errorMessage={resultQuery.data?.error ?? diagnosis?.llm_error}
              commandLabel="AWS CLI Commands"
            />
            <AwsInvestigationResults data={awsResult} />
          </>
        )}
      </div>
    </AppShell>
  );
}
