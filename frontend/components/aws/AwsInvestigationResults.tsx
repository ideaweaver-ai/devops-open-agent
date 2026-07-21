"use client";

import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import { TopologyGraph } from "@/components/topology/TopologyGraph";
import { awsTopologyToGraph } from "@/lib/awsTopologyAdapter";
import { getAwsIssueTypeLabel } from "@/lib/awsIssueTypes";
import type { AwsInvestigationResponse, AwsLambdaInvocationMetrics } from "@/types/aws";
import { ObservabilityEvidencePanel } from "@/components/ObservabilityEvidencePanel";

type ResultsTab =
  | "overview"
  | "ec2"
  | "lambda"
  | "s3"
  | "network"
  | "load_balancers"
  | "topology"
  | "cloudwatch"
  | "cloudtrail"
  | "config"
  | "observability";

const TABS: { id: ResultsTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "ec2", label: "EC2" },
  { id: "lambda", label: "Lambda" },
  { id: "s3", label: "S3" },
  { id: "network", label: "Network" },
  { id: "load_balancers", label: "Load Balancers" },
  { id: "topology", label: "Topology" },
  { id: "cloudwatch", label: "CloudWatch" },
  { id: "cloudtrail", label: "CloudTrail" },
  { id: "config", label: "Config" },
  { id: "observability", label: "Observability" },
];

interface AwsInvestigationResultsProps {
  data: AwsInvestigationResponse;
}

function StateBadge({ state }: { state?: string | null }) {
  if (!state) return null;
  const normalized = state.toLowerCase();
  const healthy = ["running", "active", "available", "ok", "in-service", "healthy"].some((s) =>
    normalized.includes(s),
  );
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[10px] font-medium uppercase ${
        healthy
          ? "border border-emerald-500/20 bg-emerald-500/10 text-emerald-200"
          : "border border-amber-500/20 bg-amber-500/10 text-amber-200"
      }`}
    >
      {state}
    </span>
  );
}

function ResourceTable({
  headers,
  rows,
  emptyMessage,
}: {
  headers: string[];
  rows: ReactNode[][];
  emptyMessage: string;
}) {
  if (rows.length === 0) {
    return <p className="text-sm text-slate-500">{emptyMessage}</p>;
  }
  return (
    <div className="overflow-x-auto rounded-xl border border-white/[0.06]">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead>
          <tr className="border-b border-white/[0.06] bg-slate-950/60">
            {headers.map((header) => (
              <th
                key={header}
                className="px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index} className="border-b border-white/[0.04] last:border-0">
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} className="px-4 py-2.5 text-slate-300">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AwsInvestigationResults({ data }: AwsInvestigationResultsProps) {
  const [activeTab, setActiveTab] = useState<ResultsTab>("overview");
  const topologyGraph = useMemo(() => awsTopologyToGraph(data.topology), [data.topology]);

  const counts = data.investigation.resource_counts;
  const collectedAt = new Date(data.investigation.collected_at).toLocaleString();
  const lambdaMetricsByName = useMemo(() => {
    const map = new Map<string, AwsLambdaInvocationMetrics>();
    for (const metric of data.cloudwatch.lambda_metrics ?? []) {
      map.set(metric.function_name, metric);
    }
    return map;
  }, [data.cloudwatch.lambda_metrics]);

  return (
    <div className="panel-accent overflow-hidden">
      <div className="border-b border-white/[0.06] px-6 py-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="panel-subtitle mb-1">Investigation Results</p>
            <h2 className="panel-title">
              {data.account.account_name ?? data.account.account_id} · {data.investigation.region}
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Collected at {collectedAt}
              {data.investigation.issue_type && (
                <> · {getAwsIssueTypeLabel(data.investigation.issue_type)}</>
              )}
            </p>
          </div>
          <span
            className={`rounded-full border px-3 py-1 text-xs font-medium ${
              data.status === "success"
                ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-200"
                : "border-amber-500/20 bg-amber-500/10 text-amber-200"
            }`}
          >
            {data.status}
          </span>
        </div>

        {data.investigation.notes.length > 0 && (
          <ul className="mt-3 space-y-1 text-xs text-slate-400">
            {data.investigation.notes.map((note) => (
              <li key={note}>• {note}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex flex-wrap gap-1 border-b border-white/[0.06] px-4 py-2">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              activeTab === tab.id
                ? "bg-orange-500/15 text-orange-200"
                : "text-slate-500 hover:bg-white/[0.04] hover:text-slate-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="p-6">
        {activeTab === "overview" && (
          <div className="space-y-6">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {Object.entries(counts).map(([key, value]) => (
                <div
                  key={key}
                  className="rounded-xl border border-white/[0.06] bg-slate-950/40 px-4 py-3"
                >
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">
                    {key.replace(/_/g, " ")}
                  </p>
                  <p className="mt-1 text-2xl font-semibold text-white">{value}</p>
                </div>
              ))}
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-white/[0.06] bg-slate-950/40 p-4">
                <h3 className="section-label mb-3">Account</h3>
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Account ID</dt>
                    <dd className="font-mono text-slate-300">{data.account.account_id}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Credential source</dt>
                    <dd className="text-slate-300">{data.account.credential_source}</dd>
                  </div>
                  {data.account.caller_arn && (
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-500">Caller ARN</dt>
                      <dd className="max-w-[60%] truncate font-mono text-xs text-slate-300">
                        {data.account.caller_arn}
                      </dd>
                    </div>
                  )}
                </dl>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-slate-950/40 p-4">
                <h3 className="section-label mb-3">Evidence Collectors</h3>
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">CloudWatch</dt>
                    <dd className={data.cloudwatch.collected ? "text-emerald-300" : "text-amber-300"}>
                      {data.cloudwatch.collected ? `Collected (${data.cloudwatch.window})` : "Not collected"}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">CloudTrail</dt>
                    <dd className={data.cloudtrail.collected ? "text-emerald-300" : "text-amber-300"}>
                      {data.cloudtrail.collected
                        ? `${data.cloudtrail.events.length} events`
                        : "Not collected"}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">AWS Config</dt>
                    <dd className={data.aws_config.enabled ? "text-emerald-300" : "text-slate-400"}>
                      {data.aws_config.enabled ? "Enabled" : "Disabled / unavailable"}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Topology nodes</dt>
                    <dd className="text-slate-300">{data.topology.graph_nodes.length}</dd>
                  </div>
                </dl>
              </div>
            </div>
          </div>
        )}

        {activeTab === "ec2" && (
          <ResourceTable
            headers={["Instance", "Type", "State", "Tags", "Private IP", "VPC", "ASG"]}
            emptyMessage="No EC2 instances discovered in this region."
            rows={data.resources.ec2_instances.map((instance) => [
              <div key={instance.instance_id}>
                <p className="font-mono text-xs">{instance.instance_id}</p>
                {instance.name && <p className="text-xs text-slate-500">{instance.name}</p>}
                {instance.state_transition_reason && (
                  <p className="mt-1 text-[11px] text-amber-300/90">
                    {instance.state_transition_reason}
                  </p>
                )}
              </div>,
              instance.instance_type ?? "—",
              <StateBadge key="state" state={instance.state} />,
              Object.keys(instance.tags ?? {}).length > 0 ? (
                <div className="space-y-0.5 text-xs">
                  {Object.entries(instance.tags ?? {}).map(([key, value]) => (
                    <p key={key} className="font-mono text-slate-400">
                      <span className="text-slate-500">{key}=</span>
                      {value}
                    </p>
                  ))}
                </div>
              ) : (
                "—"
              ),
              instance.private_ip ?? "—",
              <span className="font-mono text-xs">{instance.vpc_id ?? "—"}</span>,
              instance.auto_scaling_group ?? "—",
            ])}
          />
        )}

        {activeTab === "lambda" && (
          <ResourceTable
            headers={["Function", "Runtime", "Timeout", "State", "Errors", "Max Duration", "Timeouts"]}
            emptyMessage="No Lambda functions discovered in this region."
            rows={(data.resources.lambda_functions ?? []).map((fn) => {
              const metrics = lambdaMetricsByName.get(fn.function_name);
              const timeoutIssues =
                (metrics?.timeout_log_events ?? 0) > 0 || metrics?.duration_at_timeout;
              return [
                <div key={fn.function_arn}>
                  <p className="font-mono text-xs">{fn.function_name}</p>
                  <p className="truncate text-[11px] text-slate-500">{fn.function_arn}</p>
                  {fn.state_reason && (
                    <p className="mt-1 text-[11px] text-amber-300/90">{fn.state_reason}</p>
                  )}
                </div>,
                fn.runtime ?? "—",
                fn.timeout != null ? `${fn.timeout}s` : "—",
                <StateBadge key="state" state={fn.state} />,
                metrics?.errors != null ? String(metrics.errors) : "—",
                metrics?.max_duration_ms != null
                  ? `${Math.round(metrics.max_duration_ms)}ms`
                  : "—",
                timeoutIssues ? (
                  <span className="text-amber-300">
                    {metrics?.timeout_log_events
                      ? `${metrics.timeout_log_events} log event(s)`
                      : "duration at timeout"}
                  </span>
                ) : (
                  "—"
                ),
              ];
            })}
          />
        )}

        {activeTab === "s3" && (
          <ResourceTable
            headers={["Bucket", "Encryption", "Versioning", "Public Policy", "Logging", "Notifications"]}
            emptyMessage="No S3 buckets discovered in this region."
            rows={(data.resources.s3_buckets ?? []).map((bucket) => [
              <div key={bucket.bucket_name}>
                <p className="font-mono text-xs">{bucket.bucket_name}</p>
                {bucket.region && <p className="text-xs text-slate-500">{bucket.region}</p>}
              </div>,
              bucket.encryption_enabled == null
                ? "—"
                : bucket.encryption_enabled
                  ? bucket.encryption_type ?? "Enabled"
                  : "Disabled",
              bucket.versioning_status ?? "—",
              bucket.policy_is_public == null
                ? "—"
                : bucket.policy_is_public
                  ? "Public"
                  : "Not public",
              bucket.logging_enabled ? bucket.logging_target_bucket ?? "Enabled" : "Disabled",
              String(bucket.notifications?.length ?? 0),
            ])}
          />
        )}

        {activeTab === "network" && (
          <div className="space-y-6">
            <div>
              <h3 className="section-label mb-3">VPCs ({data.resources.vpcs.length})</h3>
              <ResourceTable
                headers={["VPC", "CIDR", "State", "Subnets"]}
                emptyMessage="No VPCs found."
                rows={data.resources.vpcs.map((vpc) => [
                  <div key={vpc.vpc_id}>
                    <p className="font-mono text-xs">{vpc.vpc_id}</p>
                    {vpc.name && <p className="text-xs text-slate-500">{vpc.name}</p>}
                  </div>,
                  vpc.cidr_block ?? "—",
                  <StateBadge key="state" state={vpc.state} />,
                  String(vpc.subnets.length),
                ])}
              />
            </div>

            <div>
              <h3 className="section-label mb-3">Internet-Exposed Ingress Rules</h3>
              {(() => {
                const exposed = data.resources.security_groups.flatMap((group) =>
                  group.ingress_rules
                    .filter((rule) =>
                      (rule.cidr_blocks as string[] | undefined)?.some(
                        (cidr) => cidr === "0.0.0.0/0" || cidr === "::/0",
                      ),
                    )
                    .map((rule, index) => ({
                      key: `${group.security_group_id}-${index}`,
                      group,
                      rule,
                    })),
                );
                return (
                  <ResourceTable
                    headers={["Security Group", "Protocol", "Port", "Source", "Attached"]}
                    emptyMessage="No internet-wide ingress rules detected."
                    rows={exposed.map(({ key, group, rule }) => [
                      <div key={key}>
                        <p className="font-mono text-xs">{group.security_group_id}</p>
                        {group.name && <p className="text-xs text-slate-500">{group.name}</p>}
                      </div>,
                      String(rule.protocol ?? "—"),
                      rule.from_port === rule.to_port
                        ? String(rule.from_port ?? "ALL")
                        : `${rule.from_port ?? "?"}-${rule.to_port ?? "?"}`,
                      ((rule.cidr_blocks as string[] | undefined) ?? []).join(", ") || "—",
                      String(group.attached_resource_ids?.length ?? 0),
                    ])}
                  />
                );
              })()}
            </div>

            <div>
              <h3 className="section-label mb-3">
                Security Groups ({data.resources.security_groups.length})
              </h3>
              <ResourceTable
                headers={["Group", "VPC", "Description", "Attached"]}
                emptyMessage="No security groups found."
                rows={data.resources.security_groups.map((group) => [
                  <div key={group.security_group_id}>
                    <p className="font-mono text-xs">{group.security_group_id}</p>
                    {group.name && <p className="text-xs text-slate-500">{group.name}</p>}
                  </div>,
                  <span className="font-mono text-xs">{group.vpc_id ?? "—"}</span>,
                  <span className="max-w-xs truncate text-xs">{group.description ?? "—"}</span>,
                  String(group.attached_resource_ids.length),
                ])}
              />
            </div>

            <div>
              <h3 className="section-label mb-3">
                Auto Scaling Groups ({data.resources.auto_scaling_groups.length})
              </h3>
              <ResourceTable
                headers={["Name", "Desired", "Current", "Instances"]}
                emptyMessage="No auto scaling groups found."
                rows={data.resources.auto_scaling_groups.map((asg) => [
                  asg.auto_scaling_group_name,
                  asg.desired_capacity ?? "—",
                  asg.current_capacity ?? "—",
                  String(asg.instance_ids.length),
                ])}
              />
            </div>
          </div>
        )}

        {activeTab === "load_balancers" && (
          <div className="space-y-6">
            <ResourceTable
              headers={["Load Balancer", "Type", "Scheme", "State", "DNS"]}
              emptyMessage="No load balancers found."
              rows={data.resources.load_balancers.map((lb) => [
                <div key={lb.load_balancer_arn}>
                  <p className="text-sm">{lb.name ?? "—"}</p>
                  <p className="max-w-xs truncate font-mono text-[10px] text-slate-500">
                    {lb.load_balancer_arn}
                  </p>
                </div>,
                lb.type ?? "—",
                lb.scheme ?? "—",
                <StateBadge key="state" state={lb.state} />,
                <span className="max-w-xs truncate font-mono text-xs">{lb.dns_name ?? "—"}</span>,
              ])}
            />

            <div>
              <h3 className="section-label mb-3">
                Target Groups ({data.resources.target_groups.length})
              </h3>
              <ResourceTable
                headers={["Name", "Protocol", "Port", "Targets", "Unhealthy"]}
                emptyMessage="No target groups found."
                rows={data.resources.target_groups.map((tg) => {
                  const unhealthy = tg.targets.filter(
                    (t) => t.health_state && t.health_state.toLowerCase() !== "healthy",
                  ).length;
                  return [
                    tg.target_group_name,
                    tg.protocol ?? "—",
                    tg.port ?? "—",
                    String(tg.targets.length),
                    unhealthy > 0 ? (
                      <span className="text-amber-300">{unhealthy}</span>
                    ) : (
                      "0"
                    ),
                  ];
                })}
              />
            </div>
          </div>
        )}

        {activeTab === "topology" && (
          <div className="space-y-4">
            {topologyGraph.relationships.length === 0 ? (
              <p className="text-sm text-slate-500">
                No topology relationships to display for this region.
              </p>
            ) : (
              <>
                <p className="text-xs text-slate-500">
                  {data.topology.graph_nodes.length} resources ·{" "}
                  {data.topology.relationships.length} relationships ·{" "}
                  {data.investigation.region}
                </p>
                <TopologyGraph data={topologyGraph} variant="aws" height={640} />
              </>
            )}
          </div>
        )}

        {activeTab === "cloudwatch" && (
          <div className="space-y-6">
            {data.cloudwatch.error && (
              <p className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
                {data.cloudwatch.error}
              </p>
            )}

            <div>
              <h3 className="section-label mb-3">
                Alarms ({data.cloudwatch.alarms.length})
              </h3>
              <ResourceTable
                headers={["Alarm", "State", "Metric", "Threshold"]}
                emptyMessage="No CloudWatch alarms in ALARM or INSUFFICIENT_DATA state."
                rows={data.cloudwatch.alarms.map((alarm) => [
                  alarm.alarm_name,
                  <StateBadge key="state" state={alarm.state_value} />,
                  alarm.metric_name ?? "—",
                  alarm.threshold ?? "—",
                ])}
              />
            </div>

            <div>
              <h3 className="section-label mb-3">
                Metrics ({data.cloudwatch.metrics.length})
              </h3>
              {data.cloudwatch.metrics.length === 0 ? (
                <p className="text-sm text-slate-500">No metrics collected.</p>
              ) : (
                <div className="space-y-3">
                  {data.cloudwatch.metrics.map((metric, index) => (
                    <div
                      key={`${metric.metric_name}-${index}`}
                      className="rounded-xl border border-white/[0.06] bg-slate-950/40 p-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="font-mono text-sm text-white">{metric.metric_name}</p>
                        <span className="text-xs text-slate-500">{metric.namespace}</span>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        {metric.datapoints.length} datapoints · window {metric.window}
                      </p>
                      {Object.keys(metric.dimensions).length > 0 && (
                        <p className="mt-2 font-mono text-[11px] text-slate-400">
                          {Object.entries(metric.dimensions)
                            .map(([k, v]) => `${k}=${v}`)
                            .join(", ")}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "cloudtrail" && (
          <div className="space-y-6">
            {data.cloudtrail.error && (
              <p className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
                {data.cloudtrail.error}
              </p>
            )}

            <p className="text-xs text-slate-500">
              Lookback: {data.cloudtrail.lookback_hours}h · Tracking stop/start/terminate and
              instance-scoped API activity
            </p>

            {(data.cloudtrail.instance_events?.length ?? 0) > 0 && (
              <div>
                <h3 className="section-label mb-3">Instance Activity (attribution)</h3>
                <ResourceTable
                  headers={["Time", "Event", "Actor", "Instances", "Tags", "Source IP"]}
                  emptyMessage="No instance-scoped CloudTrail events."
                  rows={(data.cloudtrail.instance_events ?? []).map((event, index) => [
                    event.event_time ? new Date(event.event_time).toLocaleString() : "—",
                    <span
                      key={index}
                      className={
                        event.event_name === "StopInstances" ||
                        event.event_name === "TerminateInstances"
                          ? "font-medium text-amber-200"
                          : event.event_name === "CreateTags" || event.event_name === "DeleteTags"
                            ? "font-medium text-sky-200"
                            : ""
                      }
                    >
                      {event.event_name ?? "—"}
                    </span>,
                    <div key={`actor-${index}`}>
                      <p className="text-sm">{event.username ?? "—"}</p>
                      {event.principal_arn && (
                        <p className="max-w-xs truncate font-mono text-[10px] text-slate-500">
                          {event.principal_arn}
                        </p>
                      )}
                    </div>,
                    <span className="font-mono text-xs">
                      {(event.instance_ids ?? []).join(", ") || event.resource_name || "—"}
                    </span>,
                    <span className="font-mono text-xs">{event.tag_summary ?? "—"}</span>,
                    <span className="font-mono text-xs">{event.source_ip ?? "—"}</span>,
                  ])}
                />
              </div>
            )}

            <div>
              <h3 className="section-label mb-3">All Tracked Events</h3>
              <ResourceTable
                headers={["Time", "Event", "Actor", "Resource", "Tags", "Source IP"]}
                emptyMessage="No relevant CloudTrail events in the lookback window."
                rows={data.cloudtrail.events.map((event, index) => [
                  event.event_time ? new Date(event.event_time).toLocaleString() : "—",
                  <div key={index}>
                    <p className="text-sm">{event.event_name ?? "—"}</p>
                    {event.resource_type && (
                      <p className="text-xs text-slate-500">{event.resource_type}</p>
                    )}
                  </div>,
                  event.username ?? "—",
                  event.resource_name ?? ((event.instance_ids ?? []).join(", ") || "—"),
                  <span className="font-mono text-xs">{event.tag_summary ?? "—"}</span>,
                  <span className="font-mono text-xs">{event.source_ip ?? "—"}</span>,
                ])}
              />
            </div>
          </div>
        )}

        {activeTab === "config" && (
          <div>
            {data.aws_config.error && (
              <p className="mb-4 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
                {data.aws_config.error}
              </p>
            )}
            {!data.aws_config.enabled ? (
              <p className="text-sm text-slate-500">
                AWS Config is not enabled or not accessible for this account/region.
              </p>
            ) : (
              <ResourceTable
                headers={["Resource Type", "Resource ID", "Captured"]}
                emptyMessage="No recent configuration changes recorded."
                rows={data.aws_config.recent_changes.map((change, index) => [
                  change.resource_type ?? "—",
                  <span key={index} className="font-mono text-xs">
                    {change.resource_id ?? "—"}
                  </span>,
                  change.capture_time
                    ? new Date(change.capture_time).toLocaleString()
                    : "—",
                ])}
              />
            )}
          </div>
        )}

        {activeTab === "observability" && (
          data.observability?.enabled ||
          (data.observability?.findings?.length ?? 0) > 0 ||
          data.observability?.summary ? (
            <ObservabilityEvidencePanel data={data.observability} />
          ) : (
            <p className="text-sm text-slate-500">
              No Prometheus/Grafana evidence for this investigation. Enable
              integrations under Integrations, then re-run the investigation.
            </p>
          )
        )}
      </div>
    </div>
  );
}
