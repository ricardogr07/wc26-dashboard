# Deployment

> 🏆 **The tournament is over and the backend infra has been retired.** The only
> live deployment path is `deploy-site.yml` (below). Everything after that
> section documents the full pipeline as it ran during the tournament.

## Current: static site deploy (`deploy-site.yml`)

The site is a static archive on Azure Static Web Apps. `deploy-site.yml` runs on
pushes to `main` that touch `web/**` (or manually from the Actions tab): it
builds `web/` with pnpm, logs into Azure via OIDC, fetches the SWA deployment
token at run time (`az staticwebapp secrets list`; no stored token secret), and
uploads `web/out/`.

## Retiring the backend

The frontend no longer calls the API, so the backend can be stopped or deleted
at any time without touching the site. The old on/off workflow is gone; this is
a one-shot manual operation:

```bash
# Stop the Function App (reversible, no cost while stopped on Flex Consumption)
az functionapp stop --name wc26-api --resource-group wc26-dashboard-rg

# Optional, permanent: delete the Function App and Cosmos DB.
# Do NOT run `terraform destroy`; that would also delete the Static Web App
# that serves the archive.
az functionapp delete --name wc26-api --resource-group wc26-dashboard-rg
az cosmosdb delete --name wc26-cosmos --resource-group wc26-dashboard-rg
```

## Historical: full pipeline overview

```
deploy.yml (workflow_dispatch, main only)
│
├── infra          Terraform apply → capture Function App + SWA URLs
├── deploy-api     Build + deploy Azure Functions (depends on infra)
├── smoke-api      Hit /api/health + key endpoints (depends on deploy-api)
├── deploy-web     pnpm build → deploy Static Web App (depends on infra)
└── smoke-web      Check Static Web App is reachable (depends on deploy-web)
```

Terraform always runs first. Its outputs (function app name, URLs, SWA deployment token) flow to downstream jobs via `needs.<job>.outputs`.

## Prerequisites

### Azure resources (one-time setup)

1. **Azure subscription** with Contributor access
2. **Service principal** with federated OIDC credentials for GitHub Actions (no secret rotation needed)
3. **Terraform state backend**: a storage account and container for the `prod.terraform.tfstate` file:

```bash
az group create -n wc26-tfstate-rg -l eastus2
az storage account create -n wc26tfstate -g wc26-tfstate-rg --sku Standard_LRS
az storage container create -n tfstate --account-name wc26tfstate
```

These must exist before running `terraform init`. They are intentionally outside the Terraform-managed resource group.

4. **`infra/terraform.tfvars`**: copy from the example and fill in secrets:

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars` is gitignored; never commit it.

### GitHub Secrets

Set these in **Settings → Secrets and variables → Actions**:

| Secret | Description |
|---|---|
| `AZURE_CLIENT_ID` | Service principal client ID (used for OIDC login) |
| `AZURE_TENANT_ID` | Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `THESPORTSDB_API_KEY` | TheSportsDB API key (passed to Terraform as `TF_VAR_thesportsdb_api_key`) |

`AZURE_STATIC_WEB_APPS_API_TOKEN` is **not** a stored secret; the historical pipeline read it from Terraform output, and `deploy-site.yml` fetches it at run time via `az staticwebapp secrets list`.

## Running a deploy (historical)

1. Go to **Actions → Deploy** in the GitHub UI
2. Click **Run workflow** → select `main` → confirm
3. The pipeline takes approximately 8–12 minutes end-to-end

Terraform always applies before deploying code. If no infrastructure has changed, the apply is a no-op (seconds). If you only changed application code, the `infra` job still runs but does nothing.

## Running Terraform manually

```bash
cd infra

# First-time init (also run after upgrading provider versions)
terraform init

# Preview changes
terraform plan -var="thesportsdb_api_key=YOUR_KEY"

# Apply
terraform apply -var="thesportsdb_api_key=YOUR_KEY"
```

## Infrastructure notes

### Single environment

There is one environment: **production**. The Terraform state file is `prod.terraform.tfstate`. Running `terraform apply` always touches production; there is no staging environment.

### `cosmos_free_tier`

The `cosmos_free_tier` variable defaults to `true`. Azure allows **only one free-tier Cosmos DB account per subscription**. If your subscription already has a free-tier account (from another project), set `cosmos_free_tier = false` in `terraform.tfvars`, or Terraform will fail with a quota error.

### FC1 / ARM template workaround

The Azure Functions Flex Consumption plan (FC1) is not fully supported by the `azurerm` 3.x provider. The Terraform code uses a raw ARM deployment (`infra/arm/function_app.json`) via `azurerm_resource_group_template_deployment` to work around this. When `azurerm` 4.x adds native FC1 support, this can be replaced with a direct `azurerm_linux_function_app` resource.

### `prevent_deletion_if_contains_resources = true`

The resource group has this safety guard enabled. Terraform cannot delete the resource group while it contains resources. To tear everything down:

```bash
# 1. Delete resources inside the group first
az resource list -g wc26-dashboard-rg --query "[].id" -o tsv | xargs az resource delete --ids

# 2. Then destroy via Terraform (or delete the group directly)
terraform destroy
```

## Seeding data after first deploy (historical)

During the tournament, after the first successful deploy the Cosmos container was empty and had to be seeded from a local machine:

```bash
# Point at production (set COSMOS_CONNECTION_STRING to the prod value)
export COSMOS_CONNECTION_STRING="AccountEndpoint=https://..."

uv run python scripts/seed_cosmos.py
```

This uploads all documents from `shared/seed/` (teams, participants, and group-stage fixtures). Use `--force` to overwrite if re-seeding.

## CI (pull request checks)

`ci.yml` runs on every PR:

| Job | What it checks |
|---|---|
| `ci-api` | `ruff` lint + `mypy` type-check + `pytest` (138 tests) |
| `ci-frontend` | `tsc --noEmit` + `eslint` |
| `ci-e2e` | Cypress smoke suite against stubbed API |

All three must pass before merge.
