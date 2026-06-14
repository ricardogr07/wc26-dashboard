# Local Development Setup

Two paths: **Docker Compose** (recommended, one command) or **manual** (more control).

## Prerequisites

Both paths require:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — for Azurite and the containerized API

Manual path also requires:

- Python 3.11+ and [uv](https://docs.astral.sh/uv/) — `pip install uv`
- Node.js 20+ and [pnpm](https://pnpm.io/) — `npm install -g pnpm`
- [Azure Functions Core Tools v4](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local)

---

## Option A — Docker Compose (recommended)

Starts Azurite, the API, and the Next.js dev server in one step.

### 1. Create `.env.local`

```bash
cp .env.local.example .env.local
```

Fill in the real values:

| Variable | Where to get it |
|---|---|
| `COSMOS_CONNECTION_STRING` | Azure portal → Cosmos DB → Keys → Primary Connection String |
| `ADMIN_API_KEY` | Any strong random string — used to gate `POST /api/admin/override` |
| `THESPORTSDB_API_KEY` | [thesportsdb.com](https://www.thesportsdb.com/) — free tier works |

The other variables (`COSMOS_DATABASE_NAME`, `COSMOS_CONTAINER_NAME`, `THESPORTSDB_LEAGUE_ID`, `THESPORTSDB_SEASON`, `TIMER_SCHEDULE`) have sensible defaults in `.env.local.example` and don't need to change.

`AzureWebJobsStorage` is pre-filled with the Azurite emulator connection string — don't change it for local dev.

### 2. Start the stack

```bash
docker compose up --build
```

Services:
- Azurite (Azure Storage emulator) — ports 10000–10002
- API (Azure Functions) — `http://localhost:7071`
- Web (Next.js) — `http://localhost:3000`

The API container has a healthcheck; Docker Compose waits for it to pass before the web container starts.

### 3. Seed the database (first run only)

After the stack is healthy:

```bash
# Install Python deps in a local venv
uv sync

# Seed teams, participants, and group-stage fixtures
uv run python scripts/seed_cosmos.py
```

On subsequent runs `seed_cosmos.py` skips documents that already exist. Use `--force` to overwrite everything.

### 4. Verify

Open `http://localhost:3000` — you should see the standings page. The schedule page shows the 72 group-stage fixtures. The simulate page runs a Monte Carlo simulation on first load (≈ 2 s).

---

## Option B — Manual (API + Web separately)

### API (Azure Functions)

```bash
# Copy local settings
cp api/local.settings.json.example api/local.settings.json
# Fill in COSMOS_CONNECTION_STRING, THESPORTSDB_API_KEY, ADMIN_API_KEY

# Start Azurite (required by Functions runtime)
docker compose up azurite -d

# Run all checks — lint → type-check → tests
uv tool run tox

# Start the Functions host on http://localhost:7071
func start
```

`local.settings.json` is gitignored. Never commit it.

### Web (Next.js)

```bash
cd web
pnpm install

# Dev server proxies /api/* to localhost:7071
pnpm dev
```

The Next.js dev server is at `http://localhost:3000`. API calls proxy to the Functions host.

---

## Environment Variables Reference

All API config flows through `local.settings.json` (manual path) or `.env.local` (Docker path). The two files have the same keys.

| Variable | Required | Default | Description |
|---|---|---|---|
| `COSMOS_CONNECTION_STRING` | Yes | — | Cosmos DB connection string |
| `COSMOS_DATABASE_NAME` | No | `wc26db` | Cosmos DB database name |
| `COSMOS_CONTAINER_NAME` | No | `items` | Cosmos DB container name |
| `ADMIN_API_KEY` | Yes | — | Bearer token for `POST /api/admin/override` |
| `THESPORTSDB_API_KEY` | Yes | — | TheSportsDB API key |
| `THESPORTSDB_LEAGUE_ID` | No | `4429` | League ID for WC 2026 |
| `THESPORTSDB_SEASON` | No | `2026-2027` | Season string |
| `TIMER_SCHEDULE` | No | `0 */2 * * * *` | NCRONTAB for the sync timer |
| `AzureWebJobsStorage` | Yes | *(Azurite default)* | Storage connection for Functions runtime |
| `CORS_ORIGIN` | No | `*` | Allowed CORS origin |

---

## Running Tests

```bash
# Python — lint + type-check + unit tests
uv tool run tox

# TypeScript
cd web
pnpm type-check
pnpm lint

# Cypress E2E (uses stubbed API — no live backend needed for the tests themselves)
# From the web/ directory with the Docker stack running:
pnpm e2e:docker   # runs inside the web container (Chromium + Xvfb pre-installed)

# Direct host run (requires Node.js 18 or 20; Node 22+ is incompatible with the Cypress binary)
pnpm e2e
pnpm e2e:open     # interactive mode
```

---

## Scripts

| Script | What it does |
|---|---|
| `scripts/seed_cosmos.py` | Uploads `shared/seed/` data to Cosmos. Skips existing docs by default; `--force` upserts. |
| `scripts/generate_fixtures.py` | Re-generates `shared/seed/fixtures.json` from scratch (only needed if the schedule changes). |
| `scripts/setup_emulator.py` | Creates the Cosmos DB database and container on the local emulator. |
| `scripts/smoke_all.ps1` | Hits all API endpoints and checks status codes. Useful post-deploy sanity check. |
