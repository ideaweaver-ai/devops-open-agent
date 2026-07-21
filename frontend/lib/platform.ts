export const PLATFORM = {
  name: "DevOps Open Agent",
  tagline: "Open Source AI-Powered DevOps Troubleshooting Platform",
  badges: ["Open Source", "Self-Hostable", "Cloud Agnostic", "Vendor Neutral"],
} as const;

export interface AgentNavItem {
  href: string;
  label: string;
}

export interface PlatformAgent {
  id: string;
  name: string;
  href: string;
  description: string;
  available: boolean;
  nav: AgentNavItem[];
  matchesPath: (pathname: string) => boolean;
}

export interface PlatformIntegration {
  id: string;
  name: string;
  href: string;
  description: string;
  nav: AgentNavItem[];
  matchesPath: (pathname: string) => boolean;
}

export const PLATFORM_INTEGRATIONS: PlatformIntegration = {
  id: "integrations",
  name: "Integrations",
  href: "/integrations/slack",
  description: "Connect DevOps Open Agent with Slack, Teams, PagerDuty, MCP, Qdrant, Prometheus, Grafana, and AWS Accounts.",
  nav: [
    { href: "/integrations/slack", label: "Slack" },
    { href: "/integrations/teams", label: "Microsoft Teams" },
    { href: "/integrations/pagerduty", label: "PagerDuty" },
    { href: "/integrations/mcp", label: "MCP" },
    { href: "/integrations/qdrant", label: "Qdrant (RAG)" },
    { href: "/integrations/prometheus", label: "Prometheus" },
    { href: "/integrations/grafana", label: "Grafana" },
    { href: "/integrations/aws", label: "AWS Accounts" },
  ],
  matchesPath: (pathname) => pathname.startsWith("/integrations"),
};

export const PLATFORM_AGENTS: PlatformAgent[] = [
  {
    id: "kubernetes",
    name: "Kubernetes Debugging Agent",
    href: "/",
    description: "Troubleshoot Kubernetes clusters, workloads, networking, and topology.",
    available: true,
    nav: [
      { href: "/", label: "Investigate" },
      { href: "/schedules", label: "Schedules" },
      { href: "/investigations", label: "Investigations" },
      { href: "/topology", label: "Topology" },
    ],
    matchesPath: (pathname) =>
      pathname === "/" ||
      pathname.startsWith("/schedules") ||
      (pathname.startsWith("/investigations") &&
        !pathname.startsWith("/aws") &&
        !pathname.startsWith("/cloud-cost") &&
        !pathname.startsWith("/pr-reviewer")) ||
      pathname.startsWith("/topology"),
  },
  {
    id: "aws",
    name: "AWS DevOps Agent",
    href: "/aws",
    description: "Troubleshoot AWS infrastructure across accounts and regions.",
    available: true,
    nav: [
      { href: "/aws", label: "Investigate" },
      { href: "/aws/investigations", label: "Investigations" },
      { href: "/aws/topology", label: "Topology" },
    ],
    matchesPath: (pathname) => pathname.startsWith("/aws"),
  },
  {
    id: "cloud-cost",
    name: "Cloud Cost Detector",
    href: "/cloud-cost",
    description: "Identify unused and underutilized AWS resources for cost optimization.",
    available: true,
    nav: [
      { href: "/cloud-cost", label: "Analyze" },
      { href: "/cloud-cost/investigations", label: "Investigations" },
    ],
    matchesPath: (pathname) => pathname.startsWith("/cloud-cost"),
  },
  {
    id: "pr-reviewer",
    name: "PR Reviewer",
    href: "/pr-reviewer",
    description: "AI-powered DevOps review for GitHub Pull Requests.",
    available: true,
    nav: [
      { href: "/pr-reviewer", label: "Review" },
      { href: "/pr-reviewer/investigations", label: "Investigations" },
    ],
    matchesPath: (pathname) => pathname.startsWith("/pr-reviewer"),
  },
  {
    id: "performance",
    name: "Performance Debugging",
    href: "/performance",
    description: "Debug Linux host performance over passwordless SSH.",
    available: true,
    nav: [
      { href: "/performance", label: "Debug" },
      { href: "/performance/investigations", label: "Investigations" },
    ],
    matchesPath: (pathname) => pathname.startsWith("/performance"),
  },
  {
    id: "security",
    name: "Security Scanning",
    href: "/security",
    description: "Scan container images and Kubernetes clusters for vulnerabilities.",
    available: true,
    nav: [
      { href: "/security", label: "Scan" },
      { href: "/security/investigations", label: "Investigations" },
    ],
    matchesPath: (pathname) => pathname.startsWith("/security"),
  },
];

export function getActiveAgent(pathname: string): PlatformAgent {
  return (
    PLATFORM_AGENTS.find((agent) => agent.matchesPath(pathname)) ?? PLATFORM_AGENTS[0]
  );
}

export function getActiveIntegration(pathname: string): PlatformIntegration | null {
  return PLATFORM_INTEGRATIONS.matchesPath(pathname) ? PLATFORM_INTEGRATIONS : null;
}

export function getActiveSectionName(pathname: string): string {
  const integration = getActiveIntegration(pathname);
  if (integration) {
    return integration.name;
  }
  return getActiveAgent(pathname).name;
}

export function formatAgentType(agentType?: string | null): string {
  switch (agentType?.toLowerCase()) {
    case "aws":
      return "AWS";
    case "cloud-cost":
    case "cloud_cost":
      return "Cloud Cost";
    case "pr-reviewer":
    case "pr_reviewer":
      return "PR Reviewer";
    case "performance":
      return "Performance Debugging";
    case "security":
      return "Security Scanning";
    case "kubernetes":
      return "Kubernetes";
    default:
      return agentType ? agentType : "Kubernetes";
  }
}
