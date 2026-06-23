<p align="center">
  <img src="img/devops-open-agent-icon.png" alt="DevOps Open Agent" width="128" />
</p>

# DevOps Open Agent

**DevOps Open Agent** is an open-source, self-hostable, AI-powered DevOps troubleshooting platform. It helps DevOps engineers, SREs, and platform teams investigate infrastructure issues, optimize cloud costs, and review pull requests with DevOps-focused AI guidance.

## Modules

| Module | Description |
|--------|-------------|
| **Kubernetes Debugging Agent** | Investigate clusters, workloads, networking, and topology |
| **AWS DevOps Agent** | Troubleshoot AWS infrastructure across accounts and regions |
| **Cloud Cost Detector** | Find unused and underutilized AWS resources |
| **PR Reviewer** | AI DevOps review for GitHub pull requests |

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLite, PostgreSQL (auth), shared LLM providers
- **Frontend:** Next.js 15, TypeScript, Tailwind CSS, TanStack Query
- **Runtime:** Docker Compose

Supported LLM providers: OpenAI, Anthropic, OpenRouter, Ollama

## Architecture

Application request flow: the browser talks to the Next.js frontend, which calls the FastAPI backend. The API routes requests to agent modules (Kubernetes, AWS, Cloud Cost, PR Reviewer), each using a shared AI layer and persisting results to SQLite or PostgreSQL.

![Application request flow](img/application-request-flow.png)

For full platform diagrams and module internals, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Product Tour

Walk through all four agent modules with screenshots and short descriptions:

**[Download Product Tour PDF](docs/devops-open-agent-product-tour.pdf)**

The PDF includes a cover page plus 14 numbered screenshots: Kubernetes debugging and topology, AWS investigations and topology, Cloud Cost analysis, and GitHub PR review.

To regenerate locally:

```bash
python3 scripts/build_screenshots_pdf.py
```

## Prerequisites

- macOS or Linux
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS) or Docker Engine + Compose (Linux)
- Optional: [Ollama](https://ollama.com/) for local AI
- Optional: `~/.kube/config` for Kubernetes investigations
- Optional: `~/.aws/credentials` for AWS and Cloud Cost modules
- Optional: GitHub token for PR Reviewer

### Ubuntu one-line installs

Use these commands on Ubuntu to install common dependencies before running `./install.sh`.

**Docker**

```bash
curl -fsSL https://get.docker.com | sudo sh
```

After install, add your user to the Docker group (log out/in or reboot afterward):

```bash
sudo usermod -aG docker "$USER"
```

**Ollama (local LLM)**

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Pull a model (example used by default in `backend/.env.example`):

```bash
ollama pull gemma4:e4b
```

**Kind (local Kubernetes cluster)**

```bash
curl -Lo ./kind https://kind.sigs.k8s.io/dl/latest/kind-linux-amd64 && chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind
```

**AWS CLI v2**

```bash
sudo apt update && sudo apt install -y python3 python3-pip curl unzip && curl "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o awscliv2.zip && unzip -q awscliv2.zip && sudo ./aws/install
```

Configure credentials:

```bash
aws configure
```

**kubectl**

```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && chmod +x kubectl && sudo mv kubectl /usr/local/bin/
```

> **Note:** The Kind and kubectl commands above target `linux/amd64`. On ARM64 Ubuntu, replace `amd64` with `arm64` in the download URLs.

## New host checklist

Use this flow when provisioning a **fresh Linux or EC2 host**. For local development on your laptop, see [Quick Install](#quick-install) instead.

Nothing in the repository is tied to a specific IP, AWS account, or personal credentials. You configure those per host.

### 1. Clone and enter the project

```bash
git clone https://github.com/ideaweaver-ai/devops-open-agent.git
cd devops-open-agent
```

### 2. Set public URLs (required for remote access)

Create `.env` in the **project root** (next to `docker-compose.yml`), not in `backend/`:

```bash
cp .env.compose.example .env
```

Edit with your public IP or domain:

```env
PUBLIC_API_BASE_URL=http://<YOUR_IP_OR_DOMAIN>:8000
PUBLIC_APP_URL=http://<YOUR_IP_OR_DOMAIN>:3000
```

Open security group / firewall ports **3000** (UI) and **8000** (API) for your client IP.

### 3. Configure backend secrets

```bash
cp backend/.env.example backend/.env
```

Set at minimum:

```env
JWT_SECRET=<random-secret>
DEFAULT_ADMIN_PASSWORD=<your-secure-password>
AWS_DEFAULT_REGION=<your-region>
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e4b
```

Important:

- **Do not** add a blank `AWS_PROFILE=` line — omit it entirely or set a real profile name.
- **Do not** set `KUBECONFIG_PATH=/root/.kube/config` — Docker mounts kubeconfig at `/home/kube/.kube/config` inside the container.
- Add `GITHUB_TOKEN` only if using PR Reviewer.

### 4. Configure AWS on the host

```bash
aws configure
```

Credentials are mounted into the container at `/root/.aws/`. Verify after install:

```bash
docker compose exec backend python -c "import boto3; print(boto3.client('sts').get_caller_identity())"
```

Alternatively, attach an **IAM instance role** to the EC2 instance and skip `aws configure`.

### 5. Install and start

```bash
chmod +x install.sh
./install.sh --admin-pass '<your-secure-password>'
```

Or manually:

```bash
docker compose up -d --build
```

### 6. Verify the deployment

```bash
docker compose ps
docker compose exec frontend printenv NEXT_PUBLIC_API_BASE_URL
curl -s http://127.0.0.1:8000/health
```

Sign in at `http://<YOUR_IP_OR_DOMAIN>:3000/login` with username **`admin`**.

### 7. Optional — Kubernetes (Kind)

```bash
kind create cluster --name devops-agent --config deploy/kind-devops-agent.yaml
kubectl config use-context kind-devops-agent
docker compose up -d --force-recreate backend
docker compose exec backend kubectl --kubeconfig data/kubeconfig.docker.yaml get nodes
```

See [Kubernetes on Docker / AWS](#kubernetes-on-docker--aws) if cluster checks fail.

### Per-host configuration reference

| Item | Where | Notes |
|------|--------|--------|
| Public URLs | Root `.env` | `PUBLIC_API_BASE_URL`, `PUBLIC_APP_URL` |
| Secrets / LLM / AWS region | `backend/.env` | Never commit this file |
| AWS credentials | Host `~/.aws/` or IAM role | Mounted read-only into backend |
| Kubeconfig | Host `~/.kube/` | Mounted at `/home/kube/.kube/` in container |
| Admin login | Seeded on first start | Default username `admin` |

### Troubleshooting on a new host

| Issue | Section |
|-------|---------|
| Login fails from browser | [Remote / AWS deployment](#remote--aws-deployment) |
| `config profile () could not be found` | [AWS on EC2 / Docker](#aws-on-ec2--docker) |
| Kubernetes cluster missing in UI | [Kubernetes on Docker / AWS](#kubernetes-on-docker--aws) |

## Quick Install

For **local development** (localhost). On a new remote host, use [New host checklist](#new-host-checklist) instead.

```bash
chmod +x install.sh
./install.sh
```

Custom admin password:

```bash
./install.sh --admin-pass 'MySecurePass123'
```

Configure only (no Docker build):

```bash
./install.sh --skip-build
```

The installer will:

1. Verify Docker and Compose
2. Create `backend/.env` from `backend/.env.example` if missing
3. Set default username `admin` and password
4. Generate a random `JWT_SECRET`
5. Build and start all services with Docker Compose

## Default Login

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `admin123` (or value passed to `--admin-pass`) |

Sign in at [http://<your ip>:3000/login](http://<your_ip>:3000/login).

Change the password in `backend/.env` before production:

```env
DEFAULT_ADMIN_PASSWORD=your-secure-password
```

Then restart:

```bash
docker compose up -d --force-recreate backend
```

> **Note:** If an older install already created `admin@example.com`, delete the Postgres volume or sign up a new user. Fresh installs use username `admin`.

## Manual Setup

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your secrets and provider settings
docker compose up -d --build
```

### URLs

| URL | Description |
|-----|-------------|
| http://<your_ip>:3000 | Web UI |
| http://<your_ip>:8000/health | Health check |
| http://<your_ip>:8000/docs | OpenAPI docs |

## Configuration

All backend settings live in `backend/.env` (gitignored). See `backend/.env.example` for the full list.

Common settings:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e4b

GITHUB_TOKEN=
GITHUB_WEBHOOK_SECRET=

DEFAULT_ADMIN_EMAIL=admin
DEFAULT_ADMIN_PASSWORD=admin123
JWT_SECRET=change-me
```

For PR Reviewer webhooks, point GitHub to:

```text
http://<your-host>:8000/api/v1/pr-reviewer/webhook
```

Use a tunnel (ngrok, Cloudflare Tunnel) for public GitHub delivery.

## Remote / AWS deployment

If you followed the [New host checklist](#new-host-checklist), most of this is already done. Use this section when login or API calls fail from a remote browser.

The browser must call the **public backend URL**, not `localhost`.

**Symptom:** Login shows *"Unable to sign in. Please try again."* and:

```bash
docker compose exec frontend printenv NEXT_PUBLIC_API_BASE_URL
# http://localhost:8000   ← wrong for remote browsers
```

**Fix:** Ensure root `.env` exists (see [New host checklist](#new-host-checklist)):

```bash
cp .env.compose.example .env
```

Edit with your public IP or domain:

```env
PUBLIC_API_BASE_URL=http://<YOUR_IP_OR_DOMAIN>:8000
PUBLIC_APP_URL=http://<YOUR_IP_OR_DOMAIN>:3000
```

Rebuild and restart (frontend bakes in the API URL at build time):

```bash
docker compose build frontend
docker compose up -d --force-recreate backend frontend
```

Verify:

```bash
docker compose exec frontend printenv NEXT_PUBLIC_API_BASE_URL
curl -s http://127.0.0.1:8000/health
```

**Security group:** Allow inbound **TCP 3000** and **8000** from your client IP (browser needs both).

**Test login from the server:**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin","password":"admin123"}'
```

## Kubernetes on Docker / AWS

**Do not set** `KUBECONFIG_PATH=/root/.kube/config` in `backend/.env` when using Docker Compose.

| Location | Path |
|----------|------|
| On the EC2 host (as root) | `/root/.kube/config` |
| Inside the backend container | `/home/kube/.kube/config` |

`/home/kube/` exists **inside the backend container only** — not on the EC2 host. Check the mount with:

```bash
docker compose exec backend ls -la /home/kube/.kube/config
```

Docker Compose mounts `${HOME}/.kube` → `/home/kube/.kube`. Leave `KUBECONFIG_PATH` empty in `backend/.env`.

### Why `kubectl` fails inside the container

Kind writes the API server as `https://127.0.0.1:<port>`. Inside a container, `127.0.0.1` is the container itself, not your EC2 host — so this fails:

```bash
docker compose exec backend kubectl get nodes
# dial tcp 127.0.0.1:34253: connect: connection refused
```

The app rewrites localhost to `host.docker.internal` automatically. Kind must also listen on `0.0.0.0`, not only `127.0.0.1`.

### Setup Kind on Ubuntu EC2 (recommended)

```bash
cd ~/devops-open-agent
git pull origin main

# Recreate cluster so the API is reachable from Docker
kind delete cluster --name devops-agent 2>/dev/null || true
kind create cluster --name devops-agent --config deploy/kind-devops-agent.yaml

kubectl config use-context kind-devops-agent
kubectl get nodes
```

Verify inside the backend container:

```bash
docker compose up -d --force-recreate backend

# Mount + rewritten kubeconfig
docker compose exec backend ls -la /home/kube/.kube/config
docker compose exec backend python -c "
from app.kubernetes.kubeconfig_resolver import prepare_kubeconfig
print(prepare_kubeconfig(api_host_rewrite='host.docker.internal'))
"

# Use the rewritten config (what the app uses)
docker compose exec backend kubectl --kubeconfig data/kubeconfig.docker.yaml get nodes
```

If the last command works, refresh the UI — **kubeconfig** and **cluster** should turn green.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ls: cannot access '/home/kube/'` on EC2 host | Normal — run checks with `docker compose exec backend ...` |
| `current-context is not set` | `kubectl config use-context kind-devops-agent` on the host |
| `127.0.0.1: connect refused` in container | Recreate Kind with `deploy/kind-devops-agent.yaml` |
| `kubeconfig: missing` in UI | Clear `KUBECONFIG_PATH` in `backend/.env`, ensure `/root/.kube/config` exists on host |

Remove any wrong path from `backend/.env`:

```env
KUBECONFIG_PATH=
```

## AWS on EC2 / Docker

**Error:** `The config profile () could not be found`

This happens when `backend/.env` contains an empty line:

```env
AWS_PROFILE=
```

Docker injects that as a blank profile name. **Remove that line** from `backend/.env` (or set a real profile, e.g. `AWS_PROFILE=default`).

**Recommended on EC2:** attach an **IAM instance role** with AWS read permissions and do not set `AWS_PROFILE` at all. Boto3 will use the instance role automatically.

**Alternative:** mount host credentials (already configured in `docker-compose.yml`):

```bash
aws configure   # on the EC2 host
docker compose exec backend ls -la /root/.aws/
docker compose exec backend python -c "import boto3; print(boto3.client('sts').get_caller_identity())"
```

Then restart:

```bash
docker compose up -d --force-recreate backend
```

Set region in `backend/.env` if needed:

```env
AWS_DEFAULT_REGION=us-west-2
```

## Project Structure

```text
open-devops-agent/
├── backend/              # FastAPI application
│   └── app/
│       ├── modules/      # Agent modules (aws, cloud_cost, pr_reviewer, ...)
│       ├── ai/           # Shared LLM providers
│       └── storage/      # SQLite history stores
├── frontend/             # Next.js UI
├── docker-compose.yml
├── install.sh            # macOS/Linux installer
├── docs/                 # Additional documentation
└── prompts/              # Agent prompt specs
```

## Development

**Backend:**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

## Publishing to GitHub

Only source and configuration templates should be committed. Secrets and build artifacts are excluded via `.gitignore`.

**Safe to commit:**

- `backend/app/`, `backend/requirements.txt`, `backend/Dockerfile`, `backend/.env.example`
- `frontend/` source (not `node_modules/` or `.next/`)
- `docker-compose.yml`, `install.sh`, `README.md`, `docs/`, `prompts/`, `tests/`

**Never commit:**

- `backend/.env` (API keys, tokens, passwords)
- `node_modules/`, `.next/`, `.venv/`
- `data/` and local SQLite databases
- `.cursor/` and IDE-specific files

Initialize and push:

```bash
git init
git add .
git status   # verify no secrets or build artifacts are staged
git commit -m "Initial commit: DevOps Open Agent platform"
git branch -M main
git remote add origin https://github.com/<org>/<repo>.git
git push -u origin main
```

## Useful Commands

```bash
docker compose logs -f
docker compose down
docker compose up -d --build
docker compose exec backend python -c "from app.core.config import get_settings; print(get_settings().llm_provider)"
```

## License

Open source — contributions welcome.
