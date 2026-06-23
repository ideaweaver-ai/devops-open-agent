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

## Quick Install

From the project root:

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

Sign in at [http://localhost:3000/login](http://localhost:3000/login).

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
| http://localhost:3000 | Web UI |
| http://localhost:8000/health | Health check |
| http://localhost:8000/docs | OpenAPI docs |

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

When hosting on EC2 or another remote server, the browser must call the **public backend URL**, not `localhost`.

**Symptom:** Login shows *"Unable to sign in. Please try again."* and:

```bash
docker compose exec frontend printenv NEXT_PUBLIC_API_BASE_URL
# http://localhost:8000   ← wrong for remote browsers
```

**Fix:** Create a `.env` file in the project root (next to `docker-compose.yml`):

```bash
cp .env.compose.example .env
```

Edit `.env` with your public IP or domain:

```env
PUBLIC_API_BASE_URL=http://54.202.118.240:8000
PUBLIC_APP_URL=http://54.202.118.240:3000
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

Docker Compose mounts `${HOME}/.kube` → `/home/kube/.kube` and sets `KUBECONFIG` automatically. If you set `KUBECONFIG_PATH` to a host path, the backend container cannot read it.

**Setup on Ubuntu EC2 with Kind:**

```bash
# Create a cluster (after installing kind from README)
kind create cluster --name devops-agent

# Ensure a current context is set
kubectl config get-contexts
kubectl config use-context kind-devops-agent

# Verify on the host
kubectl get nodes
```

**Verify inside the backend container:**

```bash
docker compose exec backend ls -la /home/kube/.kube/config
docker compose exec backend kubectl config current-context
docker compose exec backend kubectl get nodes
```

If you see `error: current-context is not set`, fix the kubeconfig on the **host**:

```bash
kubectl config use-context kind-devops-agent
docker compose up -d --force-recreate backend
```

Remove any wrong path from `backend/.env`:

```env
KUBECONFIG_PATH=
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
