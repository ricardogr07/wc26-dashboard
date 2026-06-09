# Quiniela Mundial 2026 Dashboard

Tournament standings dashboard for the 2026 FIFA World Cup.

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14 + TypeScript + Tailwind CSS + Recharts |
| Backend | Azure Functions (Python 3.11) |
| Database | Azure Cosmos DB (free tier) |
| Hosting | Azure Static Web Apps |
| IaC | Terraform |
| CI/CD | GitHub Actions |

## Project Docs

All planning and architecture docs live in [`.localagent/docs/`](.localagent/docs/):

- [requirements.md](.localagent/docs/requirements.md) — functional and non-functional requirements
- [roadmap.md](.localagent/docs/roadmap.md) — phased implementation plan
- [plan.md](.localagent/docs/plan.md) — architecture, data models, algorithms

## Local Development

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Node.js 20+
- [Azure Functions Core Tools v4](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local)
- [Terraform 1.9+](https://developer.hashicorp.com/terraform/install)

### API (Python)

```bash
# Run all checks (lint, typecheck, test)
uv tool run tox

# Run a single environment
uv tool run tox -e test
uv tool run tox -e lint
uv tool run tox -e typecheck

# Start Azure Functions locally
cp api/local.settings.json.example api/local.settings.json
# Fill in COSMOS_CONNECTION_STRING and other values
cd api && func start
```

### Web (Next.js)

```bash
cd web
npm install
npm run dev        # dev server on http://localhost:3000
npm run build      # static export to web/out/
npm run type-check
npm run lint
```

### Infrastructure

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# Fill in terraform.tfvars

terraform init
terraform plan
terraform apply
```

## CI/CD

- **Every PR:** `ci.yml` runs `tox` (Python) and `type-check + lint` (TypeScript)
- **Push to `main`:** `deploy.yml` runs Terraform apply, deploys Functions, deploys Static Web App

Required GitHub secrets:

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
├── .github/workflows/    CI and deploy workflows
├── .localagent/docs/     Requirements, roadmap, architecture plan
├── api/                  Azure Functions (Python)
├── infra/                Terraform
├── shared/seed/          Participant assignments, team Elo ratings
└── web/                  Next.js frontend
```
