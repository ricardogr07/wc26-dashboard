# Quiniela Mundial 2026 Dashboard

Tournament standings dashboard for the 2026 FIFA World Cup — tracks scores, team ownership, match schedule, and win probabilities for 5 participants.

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16 + TypeScript + Tailwind CSS + Recharts |
| Backend | Azure Functions (Python 3.11) |
| Database | Azure Cosmos DB (free tier) |
| Hosting | Azure Static Web Apps |
| IaC | Terraform |
| CI/CD | GitHub Actions |

## Features

- **Standings** — ranked table with each participant's score and team ownership pills
- **Schedule** — full match list with round filter and participant team highlights
- **Teams** — ownership grid sortable by participant, name, or score; filterable by status
- **Simulation** — Monte Carlo win probabilities (10 k runs) with a **Scenario Builder** to fix hypothetical match outcomes and compare shifted probabilities against the baseline
- Bilingual UI (English / Spanish)

## Local Development

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Node.js 20+ and [pnpm](https://pnpm.io/) — `npm install -g pnpm`
- [Azure Functions Core Tools v4](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local)
- [Terraform 1.9+](https://developer.hashicorp.com/terraform/install) (infrastructure changes only)

### 1. API (Python / Azure Functions)

```bash
# Copy and fill in COSMOS_CONNECTION_STRING and THESPORTSDB_API_KEY
cp api/local.settings.json.example api/local.settings.json

# Run all checks (lint → typecheck → tests)
uv tool run tox

# Start the Functions host on http://localhost:7071
cd api && func start
```

### 2. Web (Next.js)

```bash
cd web
pnpm install

# Dev server on http://localhost:3000 (proxies /api/* to localhost:7071)
pnpm dev

# Static export to web/out/
pnpm build

# Type-check and lint
pnpm type-check
pnpm lint

# E2E tests (Cypress, uses stubbed API — no live backend needed)
pnpm e2e
pnpm e2e:open   # interactive mode
```

### 3. Infrastructure (optional — for infra changes only)

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# Fill in terraform.tfvars

terraform init
terraform plan
terraform apply
```

## CI/CD

| Trigger | Workflow | What it does |
|---------|----------|--------------|
| Every PR | `ci.yml` | API: tox (lint + typecheck + tests). Web: type-check + lint. E2E: Cypress smoke suite. |
| Push to `main` | `deploy.yml` | Terraform apply → deploy Azure Functions → smoke test API → deploy Static Web App → smoke test web |

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | Service principal client ID (OIDC) |
| `AZURE_TENANT_ID` | Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | Static Web App deployment token |
| `THESPORTSDB_API_KEY` | TheSportsDB API key |

## Repository Structure

```
wc26-dashboard/
├── .github/
│   ├── actions/          Reusable composite actions (ci-api, ci-frontend, ci-e2e)
│   └── workflows/        ci.yml (PR checks), deploy.yml (push to main)
├── .localagent/docs/     Architecture notes, requirements, roadmap
├── api/
│   ├── handlers/         One module per endpoint (standings, matches, simulate, …)
│   ├── models/           Pydantic models (Match, Participant, Team, SimulationRun)
│   ├── simulation/       Monte Carlo engine + bracket logic
│   ├── tests/            pytest suite
│   └── function_app.py   Azure Functions entry point
├── infra/                Terraform (Cosmos DB, Functions, Static Web App)
├── shared/seed/          Participant assignments + initial team Elo ratings
└── web/
    ├── app/              Next.js App Router pages (/, /schedule, /teams, /simulate)
    ├── components/       Shared React components + shadcn/ui
    └── lib/              API client, types, translations, utilities
```
