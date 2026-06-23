# DevOps Open Agent — Platform Architecture

Open Source · Self Hostable · Cloud Agnostic · Vendor Neutral

**Tagline:** Open Source AI-Powered DevOps Troubleshooting Platform

## System context

```mermaid
flowchart TB
    subgraph clients["Clients"]
        User["Browser / DevOps engineer"]
        GitHub["GitHub (PR webhooks)"]
    end

    subgraph compose["Docker Compose"]
        FE["frontend — Next.js 15 :3000"]
        BE["backend — FastAPI :8000"]
        PG["postgres — auth :5432"]
        SQLITE[("SQLite volume<br/>investigations.db")]
    end

    subgraph host["Host machine"]
        KCFG["~/.kube/config"]
        AWS["~/.aws/credentials"]
        OLLAMA["Ollama :11434"]
    end

    subgraph cloud["External services"]
        K8S["Kubernetes API"]
        AWSAPI["AWS APIs (boto3)"]
        GHAPI["GitHub API"]
        LLM["LLM providers<br/>OpenAI · Anthropic · OpenRouter · Ollama"]
    end

    User --> FE
    FE -->|"REST /api/v1 + JWT"| BE
    GitHub -->|"POST /pr-reviewer/webhook"| BE
    BE --> PG
    BE --> SQLITE
    BE --> KCFG
    BE --> AWS
    BE --> OLLAMA
    BE --> K8S
    BE --> AWSAPI
    BE --> GHAPI
    BE --> LLM
```

## Application layers

```mermaid
flowchart TB
    subgraph ui["Frontend (frontend/)"]
        Pages["Pages: /, /aws, /cloud-cost, /pr-reviewer"]
        AuthUI["Login / Signup"]
        Platform["Agent switcher — lib/platform.ts"]
    end

    subgraph api["FastAPI platform (backend/app/)"]
        Router["API v1 routers — main.py"]
        Auth["auth/ + db/ — JWT, users"]
        Jobs["InvestigationJobService"]
        Store["storage/ — SQLite abstraction"]
        SharedAI["ai/ — LLM factory + RCA pipeline"]
        Graph["graph/ — topology framework"]
    end

    subgraph agents["Agent modules"]
        K8S["kubernetes/ + api/v1/clusters, diagnose, topology"]
        AWS["modules/aws/"]
        COST["modules/cloud_cost_detector/"]
        PR["modules/pr_reviewer/"]
    end

    Pages --> Router
    AuthUI --> Auth
    Router --> Auth
    Router --> K8S
    Router --> AWS
    Router --> COST
    Router --> PR
    K8S --> SharedAI
    AWS --> SharedAI
    COST --> SharedAI
    PR --> SharedAI
    K8S --> Store
    AWS --> Store
    COST --> Store
    PR --> Store
    K8S --> Graph
    AWS --> Graph
    Jobs --> Store
```

## Agent modules

| Module | Backend path | API prefix | Frontend routes |
|--------|--------------|------------|-----------------|
| **Kubernetes Debugging** | `kubernetes/`, `api/v1/clusters`, `diagnose`, `topology` | `/api/v1/clusters`, `/diagnose`, `/topology` | `/`, `/investigations`, `/topology` |
| **AWS DevOps** | `modules/aws/` | `/api/v1/aws/*` | `/aws`, `/aws/investigations`, `/aws/topology` |
| **Cloud Cost Detector** | `modules/cloud_cost_detector/` | `/api/v1/cloud-cost-detector/*` | `/cloud-cost`, `/cloud-cost/investigations` |
| **PR Reviewer** | `modules/pr_reviewer/` | `/api/v1/pr-reviewer/*` | `/pr-reviewer`, `/pr-reviewer/investigations` |

Agent configuration: `frontend/lib/platform.ts`

## Shared AI pipeline

Every agent follows the same analysis pattern:

```mermaid
flowchart LR
    A["Evidence collection"] --> B["Context builder"]
    B --> C["Prompt builder"]
    C --> D["LLM provider"]
    D --> E["Root cause / review analysis"]
    E --> F["Confidence engine"]
    F --> G["Recommended actions"]
```

**LLM providers** (configured in `backend/.env`):

```env
LLM_PROVIDER=openai|anthropic|ollama|openrouter
```

Implementation: `backend/app/ai/llm_factory.py`

Each module may add its own prompt builder and context builder under `modules/<agent>/ai/`.

## Data architecture

```mermaid
flowchart LR
    subgraph postgres["PostgreSQL"]
        Users["users"]
        Sessions["auth state"]
    end

    subgraph sqlite["SQLite — data/investigations.db"]
        Inv["investigation history"]
        Jobs["investigation jobs"]
        PR["pr_reviews"]
    end

    AuthSvc["auth_service"] --> postgres
    InvStore["SQLiteInvestigationStore"] --> sqlite
    PRStore["PrReviewStore"] --> sqlite
    JobSvc["InvestigationJobService"] --> sqlite
```

| Store | Technology | Purpose |
|-------|------------|---------|
| Auth | PostgreSQL (`POSTGRES_URL`) | Users, password hashes, JWT |
| Investigations | SQLite (`DATABASE_PATH`) | Per-agent investigation history with `agent_type` |
| PR reviews | SQLite (same file) | GitHub PR review records and status |

Storage factory: `backend/app/storage/factory.py`

## Deployment topology

```mermaid
flowchart TB
    subgraph ec2["EC2 / Linux host"]
        ENV["Root .env<br/>PUBLIC_API_BASE_URL<br/>PUBLIC_APP_URL"]
        BENV["backend/.env<br/>secrets, LLM, region"]
        DC["docker compose up"]

        subgraph containers["Containers"]
            F["frontend"]
            B["backend"]
            P["postgres"]
        end

        Mounts["Volume mounts<br/>~/.kube → /home/kube/.kube<br/>~/.aws → /root/.aws"]
    end

    ENV --> F
    BENV --> B
    DC --> containers
    Mounts --> B
    F -->|"browser calls public URL"| B
```

Key deployment notes:

- Frontend bakes `NEXT_PUBLIC_API_BASE_URL` at **build time** — rebuild after changing public URLs.
- Kubeconfig localhost addresses are rewritten to `host.docker.internal` for in-container access.
- Do not set blank `AWS_PROFILE=` in `backend/.env`; use IAM role or host `aws configure`.

See [README — New host checklist](../README.md#new-host-checklist) for setup steps.

## Kubernetes agent internals

```mermaid
flowchart TB
    API["/api/v1/clusters, /diagnose, /topology"] --> CM["cluster_manager"]
    CM --> KD["cluster_discovery"]
    CM --> KCR["kubeconfig_resolver"]
    Diagnose["diagnosis_service"] --> Inv["kubernetes/investigator"]
    Inv --> Pod["pod_inspector"]
    Inv --> Dep["deployment_inspector"]
    Inv --> Net["network_inspector"]
    Inv --> Ev["events_analyzer"]
    Inv --> Logs["logs_collector"]
    Topo["topology_service"] --> TB["graph/topology_builder"]
    Diagnose --> AI["app/ai/root_cause_analyzer"]
```

## AWS & Cloud Cost internals

```mermaid
flowchart TB
    AWSAPI["/api/v1/aws/*"] --> AWSInv["AWSInvestigationService"]
    AWSInv --> Disc["discovery/ — EC2, VPC, LB, ASG"]
    AWSInv --> Coll["collectors/ — CloudTrail, CloudWatch"]
    AWSInv --> Topo["topology/builder"]
    AWSInv --> RCA["modules/aws/ai/"]

    COSTAPI["/api/v1/cloud-cost-detector/*"] --> CostSvc["cost_analysis_service"]
    CostSvc --> AWSDisc["discovery/aws_discovery"]
    CostSvc --> CE["collectors/cost_explorer"]
    CostSvc --> Unused["analysis/unused_resource_analyzer"]
    CostSvc --> CostAI["modules/cloud_cost_detector/ai/"]
    AWSDisc --> AWSAPIs["boto3 clients"]
    CE --> AWSAPIs
```

## PR Reviewer internals

```mermaid
sequenceDiagram
    participant GH as GitHub
    participant API as FastAPI webhook
    participant WH as webhook_handler
    participant GC as github_client
    participant AI as review_analyzer
    participant DB as pr_review_store

    GH->>API: POST /pr-reviewer/webhook
    API->>WH: verify signature
    WH->>GC: fetch PR files + diff
    GC->>AI: classify + build prompt
    AI->>DB: save review + status
    Note over API,DB: Manual review via POST /pr-reviewer/review
```

## Shared platform (reuse across agents)

| Layer | Current location | Notes |
|-------|------------------|-------|
| LLM providers | `backend/app/ai/` | Shared factory for all modules |
| Database | `backend/app/storage/`, `app/db/` | SQLite + Postgres split |
| Topology framework | `backend/app/graph/` | K8s + AWS topology graphs |
| Memory | `backend/app/memory/` | Stub for incident memory |
| Observability | `backend/app/observability/` | Stub collectors (Prometheus, Loki, etc.) |
| Auth | `backend/app/auth/`, `app/db/` | JWT middleware on protected routes |
| Agent framework | `backend/app/agents/` | Planner / investigator stubs |

## Investigation history

Shared history fields:

- Investigation ID
- **agent_type** (`kubernetes`, `aws`, `cloud-cost`, `pr-reviewer`)
- Timestamp, root cause, confidence, status

## Security

- Never expose API keys, secrets, or Kubernetes secret values in API responses.
- Never auto-execute remediation — human approval required.
- `backend/.env` is gitignored; use `backend/.env.example` as template.
- GitHub webhook signatures verified in `modules/pr_reviewer/github/signature.py`.

## Constraints

No vendor lock-in, proprietary dependencies, or closed-source services required for core operation.

## Adding a new agent

1. Add agent to `frontend/lib/platform.ts`
2. Create `backend/app/modules/<agent>/` with router, services, models
3. Register API router in `backend/app/main.py`
4. Implement discovery → investigation → topology → AI using shared `app/ai/`
5. Store investigations with `agent_type=<agent>`
