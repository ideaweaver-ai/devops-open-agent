import {
  Card,
  CardBody,
  CardHeader,
  H1,
  Stack,
  Text,
  computeDAGLayout,
  useHostTheme,
} from "cursor/canvas";
import type { CanvasHostTheme } from "cursor/canvas";

type NodeMeta = {
  label: string;
  subtitle?: string;
  tone?: "accent" | "neutral" | "muted";
};

const REQUEST_NODES: Record<string, NodeMeta> = {
  user: { label: "User", subtitle: "Browser UI", tone: "accent" },
  frontend: { label: "Next.js Frontend", subtitle: "/aws, /cloud-cost, /pr-reviewer", tone: "neutral" },
  api: { label: "FastAPI /api/v1", subtitle: "REST + JWT auth", tone: "neutral" },
  k8s: { label: "K8s Agent", subtitle: "clusters, diagnose, topology", tone: "neutral" },
  aws: { label: "AWS Agent", subtitle: "EC2, VPC, LB, CloudTrail", tone: "neutral" },
  cost: { label: "Cloud Cost", subtitle: "discovery + savings", tone: "neutral" },
  pr: { label: "PR Reviewer", subtitle: "webhook + manual review", tone: "neutral" },
  pg: { label: "PostgreSQL", subtitle: "users + sessions", tone: "muted" },
  ai: { label: "Shared AI Layer", subtitle: "context, prompts, RCA", tone: "accent" },
  sqlite: { label: "SQLite", subtitle: "investigations, PR reviews", tone: "muted" },
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

const NODE_WIDTH = 200;
const NODE_HEIGHT = 56;

function nodeFill(tone: NodeMeta["tone"], theme: CanvasHostTheme) {
  if (tone === "accent") return theme.fill.tertiary;
  if (tone === "muted") return theme.bg.elevated;
  return theme.fill.secondary;
}

function nodeStroke(tone: NodeMeta["tone"], theme: CanvasHostTheme) {
  if (tone === "accent") return theme.accent.primary;
  return theme.stroke.secondary;
}

function ApplicationRequestFlowDiagram() {
  const theme = useHostTheme();
  const layout = computeDAGLayout({
    nodes: Object.keys(REQUEST_NODES).map((id) => ({ id })),
    edges: REQUEST_EDGES,
    direction: "vertical",
    nodeWidth: NODE_WIDTH,
    nodeHeight: NODE_HEIGHT,
    rankGap: 80,
    nodeGap: 32,
    padding: 24,
  });

  return (
    <svg width={layout.width} height={layout.height} viewBox={`0 0 ${layout.width} ${layout.height}`}>
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
        const meta = REQUEST_NODES[node.id];
        if (!meta) return null;
        return (
          <g key={node.id}>
            <rect
              x={node.x}
              y={node.y}
              width={NODE_WIDTH}
              height={NODE_HEIGHT}
              rx={8}
              fill={nodeFill(meta.tone, theme)}
              stroke={nodeStroke(meta.tone, theme)}
              strokeWidth={1}
            />
            <text
              x={node.x + NODE_WIDTH / 2}
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
                x={node.x + NODE_WIDTH / 2}
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

export default function ApplicationRequestFlow() {
  return (
    <Stack gap={20} style={{ padding: 32, maxWidth: 1100, margin: "0 auto" }}>
      <Stack gap={8}>
        <H1>DevOps Open Agent</H1>
        <Text tone="secondary">
          Application request flow — browser to agents, shared AI layer, and data stores.
        </Text>
      </Stack>

      <Card>
        <CardHeader>Application request flow</CardHeader>
        <CardBody style={{ display: "flex", justifyContent: "center", overflowX: "auto" }}>
          <ApplicationRequestFlowDiagram />
        </CardBody>
      </Card>
    </Stack>
  );
}
