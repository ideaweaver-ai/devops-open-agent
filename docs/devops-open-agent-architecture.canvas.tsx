import {
  Card,
  CardBody,
  CardHeader,
  Divider,
  Grid,
  H1,
  H3,
  Pill,
  Row,
  Stack,
  Text,
  computeDAGLayout,
  mergeStyle,
  useHostTheme,
} from "cursor/canvas";
import type { CanvasHostTheme } from "cursor/canvas";

type NodeMeta = {
  label: string;
  subtitle?: string;
  tone?: "accent" | "neutral" | "muted";
};

const DEPLOY_NODES: NodeMeta[] = [
  { label: "Browser", subtitle: "port 3000 / 8000", tone: "accent" },
  { label: "frontend", subtitle: "Next.js 15", tone: "neutral" },
  { label: "backend", subtitle: "FastAPI", tone: "neutral" },
  { label: "postgres", subtitle: "Auth DB", tone: "neutral" },
  { label: "Host mounts", subtitle: "~/.kube, ~/.aws", tone: "muted" },
  { label: "Ollama", subtitle: "host.docker.internal", tone: "muted" },
];

const REQUEST_NODES: Record<string, NodeMeta> = {
  user: { label: "User", subtitle: "Browser UI", tone: "accent" },
  frontend: { label: "Next.js Frontend", subtitle: "/aws, /cloud-cost, /pr-reviewer", tone: "neutral" },
  api: { label: "FastAPI /api/v1", subtitle: "REST + JWT auth", tone: "neutral" },
  k8s: { label: "K8s Agent", subtitle: "clusters, diagnose, topology", tone: "neutral" },
  aws: { label: "AWS Agent", subtitle: "EC2, VPC, LB, CloudTrail", tone: "neutral" },
  cost: { label: "Cloud Cost", subtitle: "discovery + savings", tone: "neutral" },
  pr: { label: "PR Reviewer", subtitle: "webhook + manual review", tone: "neutral" },
  ai: { label: "Shared AI Layer", subtitle: "context, prompts, RCA", tone: "accent" },
  sqlite: { label: "SQLite", subtitle: "investigations, PR reviews", tone: "muted" },
  pg: { label: "PostgreSQL", subtitle: "users + sessions", tone: "muted" },
};

const REQUEST_EDGES = [
  { from: "user", to: "frontend" },
  { from: "frontend", to: "api" },
  { from: "api", to: "k8s" },
  { from: "api", to: "aws" },
  { from: "api", to: "cost" },
  { from: "api", to: "pr" },
  { from: "api", to: "pg" },
  { from: "k8s", to: "ai" },
  { from: "aws", to: "ai" },
  { from: "cost", to: "ai" },
  { from: "pr", to: "ai" },
  { from: "k8s", to: "sqlite" },
  { from: "aws", to: "sqlite" },
  { from: "cost", to: "sqlite" },
  { from: "pr", to: "sqlite" },
];

const EXTERNAL_NODES: Record<string, NodeMeta> = {
  k8sApi: { label: "Kubernetes API", subtitle: "kubeconfig mount", tone: "neutral" },
  awsApi: { label: "AWS APIs", subtitle: "boto3 / IAM role", tone: "neutral" },
  github: { label: "GitHub", subtitle: "API + webhooks", tone: "neutral" },
  llm: { label: "LLM Providers", subtitle: "Ollama, OpenAI, Anthropic, OpenRouter", tone: "accent" },
};

const EXTERNAL_EDGES = [
  { from: "k8s", to: "k8sApi" },
  { from: "aws", to: "awsApi" },
  { from: "cost", to: "awsApi" },
  { from: "pr", to: "github" },
  { from: "ai", to: "llm" },
];

const AI_STEPS = [
  "Evidence collection",
  "Context builder",
  "Prompt builder",
  "LLM provider",
  "Root cause analysis",
  "Confidence engine",
  "Recommended actions",
];

function nodeFill(tone: NodeMeta["tone"], theme: CanvasHostTheme) {
  if (tone === "accent") return theme.fill.tertiary;
  if (tone === "muted") return theme.bg.elevated;
  return theme.fill.secondary;
}

function nodeStroke(tone: NodeMeta["tone"], theme: CanvasHostTheme) {
  if (tone === "accent") return theme.accent.primary;
  return theme.stroke.secondary;
}

function DagDiagram({
  nodes,
  edges,
  width,
  height,
  nodeWidth = 188,
  nodeHeight = 56,
}: {
  nodes: Record<string, NodeMeta>;
  edges: Array<{ from: string; to: string }>;
  width: number;
  height: number;
  nodeWidth?: number;
  nodeHeight?: number;
}) {
  const theme = useHostTheme();
  const layout = computeDAGLayout({
    nodes: Object.keys(nodes).map((id) => ({ id })),
    edges,
    direction: "vertical",
    nodeWidth,
    nodeHeight,
    rankGap: 72,
    nodeGap: 28,
    padding: 16,
  });

  return (
    <svg width={width} height={height} viewBox={`0 0 ${layout.width} ${layout.height}`}>
      {layout.edges.map((edge) => (
        <line
          key={`${edge.from}-${edge.to}`}
          x1={edge.sourceX}
          y1={edge.sourceY}
          x2={edge.targetX}
          y2={edge.targetY}
          stroke={theme.stroke.secondary}
          strokeWidth={1.5}
          strokeDasharray={edge.isBackEdge ? "6 4" : undefined}
        />
      ))}
      {layout.nodes.map((node) => {
        const meta = nodes[node.id];
        if (!meta) return null;
        return (
          <g key={node.id}>
            <rect
              x={node.x}
              y={node.y}
              width={nodeWidth}
              height={nodeHeight}
              rx={8}
              fill={nodeFill(meta.tone, theme)}
              stroke={nodeStroke(meta.tone, theme)}
              strokeWidth={1}
            />
            <text
              x={node.x + nodeWidth / 2}
              y={node.y + 22}
              textAnchor="middle"
              fill={theme.text.primary}
              fontSize={12}
              fontWeight={600}
            >
              {meta.label}
            </text>
            {meta.subtitle ? (
              <text
                x={node.x + nodeWidth / 2}
                y={node.y + 40}
                textAnchor="middle"
                fill={theme.text.secondary}
                fontSize={10}
              >
                {meta.subtitle}
              </text>
            ) : null}
          </g>
        );
      })}
    </svg>
  );
}

export default function DevOpsOpenAgentArchitecture() {
  const theme = useHostTheme();

  const requestLayout = computeDAGLayout({
    nodes: Object.keys(REQUEST_NODES).map((id) => ({ id })),
    edges: REQUEST_EDGES,
    direction: "vertical",
    nodeWidth: 188,
    nodeHeight: 56,
    rankGap: 72,
    nodeGap: 28,
    padding: 16,
  });

  const externalLayout = computeDAGLayout({
    nodes: Object.keys(EXTERNAL_NODES).map((id) => ({ id })),
    edges: EXTERNAL_EDGES,
    direction: "vertical",
    nodeWidth: 188,
    nodeHeight: 56,
    rankGap: 56,
    nodeGap: 24,
    padding: 16,
  });

  return (
    <Stack gap={24} style={{ padding: 24, maxWidth: 1180 }}>
      <Stack gap={8}>
        <H1>DevOps Open Agent — Architecture</H1>
        <Text tone="secondary">
          Self-hostable platform: Next.js UI, FastAPI backend, four agent modules, shared AI layer,
          SQLite investigation history, PostgreSQL auth, Docker Compose runtime.
        </Text>
      </Stack>

      <Card>
        <CardHeader>Docker Compose deployment</CardHeader>
        <CardBody>
          <Grid columns={3} gap={12}>
            {DEPLOY_NODES.map((node) => (
              <div
                key={node.label}
                style={mergeStyle(
                  {
                    display: "flex",
                    flexDirection: "column",
                    gap: 4,
                    padding: 12,
                    borderRadius: 8,
                    border: `1px solid ${nodeStroke(node.tone, theme)}`,
                    background: nodeFill(node.tone, theme),
                  },
                  undefined,
                )}
              >
                <Text weight="semibold">{node.label}</Text>
                {node.subtitle ? <Text size="small" tone="secondary">{node.subtitle}</Text> : null}
              </div>
            ))}
          </Grid>
          <Divider />
          <Row gap={8} wrap>
            <Pill tone="neutral">PUBLIC_API_BASE_URL baked into frontend build</Pill>
            <Pill tone="neutral">CORS from root .env + backend/.env</Pill>
            <Pill tone="neutral">kubeconfig rewritten for host.docker.internal</Pill>
          </Row>
        </CardBody>
      </Card>

      <Row gap={20} align="start" wrap>
        <Card style={{ flex: 1, minWidth: 360 }}>
          <CardHeader>Application request flow</CardHeader>
          <CardBody>
            <DagDiagram
              nodes={REQUEST_NODES}
              edges={REQUEST_EDGES}
              width={requestLayout.width}
              height={requestLayout.height}
            />
          </CardBody>
        </Card>

        <Card style={{ flex: 1, minWidth: 320 }}>
          <CardHeader>External integrations</CardHeader>
          <CardBody>
            <DagDiagram
              nodes={EXTERNAL_NODES}
              edges={EXTERNAL_EDGES}
              width={externalLayout.width}
              height={externalLayout.height}
            />
            <Divider />
            <Text size="small" tone="secondary">
              GitHub delivers PR webhooks to POST /api/v1/pr-reviewer/webhook. AWS and Kubernetes
              credentials are read from host mounts — not stored in the repo.
            </Text>
          </CardBody>
        </Card>
      </Row>

      <Card>
        <CardHeader>Shared AI pipeline (all agents)</CardHeader>
        <CardBody>
          <Row gap={8} wrap>
            {AI_STEPS.map((step, index) => (
              <div key={step} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Pill tone={index === 3 ? "info" : "neutral"}>{step}</Pill>
                {index < AI_STEPS.length - 1 ? (
                  <Text tone="secondary">→</Text>
                ) : null}
              </div>
            ))}
          </Row>
        </CardBody>
      </Card>

      <Grid columns={2} gap={16}>
        <Card>
          <CardHeader>Agent modules</CardHeader>
          <CardBody>
            <Stack gap={10}>
              <Stack gap={2}>
                <H3>Kubernetes Debugging</H3>
                <Text size="small" tone="secondary">
                  backend/app/kubernetes — cluster discovery, pod/deployment inspection, events,
                  network, topology graph, RCA via app/ai.
                </Text>
              </Stack>
              <Stack gap={2}>
                <H3>AWS DevOps</H3>
                <Text size="small" tone="secondary">
                  modules/aws — EC2, VPC, load balancers, CloudTrail, CloudWatch, topology builder.
                </Text>
              </Stack>
              <Stack gap={2}>
                <H3>Cloud Cost Detector</H3>
                <Text size="small" tone="secondary">
                  modules/cloud_cost_detector — resource discovery, Cost Explorer, unused resource
                  analysis, savings estimates.
                </Text>
              </Stack>
              <Stack gap={2}>
                <H3>PR Reviewer</H3>
                <Text size="small" tone="secondary">
                  modules/pr_reviewer — GitHub client, webhook handler, file classifier, DevOps-focused
                  AI review.
                </Text>
              </Stack>
            </Stack>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>Data stores</CardHeader>
          <CardBody>
            <Stack gap={10}>
              <Stack gap={2}>
                <H3>PostgreSQL</H3>
                <Text size="small" tone="secondary">
                  Users, JWT auth, default admin seeding. Service: postgres in docker-compose.yml.
                </Text>
              </Stack>
              <Stack gap={2}>
                <H3>SQLite (backend-data volume)</H3>
                <Text size="small" tone="secondary">
                  Investigation jobs and history, PR review records. Path: data/investigations.db via
                  storage/ abstraction.
                </Text>
              </Stack>
              <Stack gap={2}>
                <H3>Investigation job service</H3>
                <Text size="small" tone="secondary">
                  Async job tracking shared across agents with agent_type discriminator
                  (kubernetes, aws, cloud-cost, pr-reviewer).
                </Text>
              </Stack>
            </Stack>
          </CardBody>
        </Card>
      </Grid>
    </Stack>
  );
}
