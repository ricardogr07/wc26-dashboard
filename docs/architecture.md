# Architecture

> 🏆 **The tournament is over and the backend has been retired.** This document
> describes the system as it ran during the tournament. The site now serves a
> frozen snapshot; see [Static archive](#static-archive-current-state) below.

## Static archive (current state)

After the final, the last responses of `/api/standings`, `/api/matches`, and
`/api/simulate` were saved as JSON snapshots under `web/public/data/`, and
`web/lib/api.ts` was pointed at them:

```
  Browser ──► GET /data/standings.json ┐
              GET /data/matches.json   ├─ static files, baked at freeze time
              GET /data/simulation.json┘         (Azure Static Web Apps)
```

No Functions, no Cosmos, no environment variables: the pages render the final
tournament state from those three files. Everything below this point is the
historical architecture.

## System Overview (as it ran during the tournament)

```
                        ┌─────────────────────┐
  TheSportsDB API ──────►  Timer trigger       │
  (match results)       │  sync_matches        │  Azure Functions
                        │  (every 2 hours)     │  (Python 3.11, FC1)
                        │                      │
  Browser ─────────────►  HTTP endpoints       │
  POST /api/simulate    │  standings           ├──────► Azure Cosmos DB
  GET  /api/standings   │  matches             │        (SQL API, /type)
  GET  /api/matches     │  simulate            │
  POST /api/admin/...   │  admin/override      │
                        └─────────────────────┘
                                  ▲
                                  │ NEXT_PUBLIC_API_BASE_URL
                        ┌─────────────────────┐
                        │  Next.js 16          │
                        │  (static export)     │  Azure Static Web Apps
                        │  /                   │  (Free tier)
                        │  /schedule           │
                        │  /teams              │
                        │  /simulate           │
                        └─────────────────────┘
```

## Components

### Azure Functions (API)

- **Runtime**: Python 3.11, Flex Consumption plan (FC1)
- **Entry point**: `function_app.py`, which registers all routes on a single `FunctionApp` instance
- **Handler pattern**: each route delegates to `api/handlers/<name>.py` which imports from `api/models/`, `api/cosmos.py`, and `api/scoring.py`

| Route | Handler | Auth |
|---|---|---|
| `GET /api/health` | inline | anonymous |
| `GET /api/standings` | `handlers/standings.py` | anonymous |
| `GET /api/matches` | `handlers/matches.py` | anonymous |
| `POST /api/simulate` | `handlers/simulate.py` | anonymous |
| `POST /api/admin/override` | `handlers/admin_override.py` | function key |
| Timer (NCRONTAB) | `handlers/sync.py` | internal |
| `OPTIONS *` | inline | anonymous (CORS preflight) |

The Cosmos client is a module-level singleton initialized with double-checked locking (`api/cosmos.py`). CORS headers are cached at module level after the first call (`api/cors.py`).

### Azure Cosmos DB

- **API**: SQL (NoSQL)
- **Database**: `wc26db`
- **Container**: `items`, partition key `/type`

All documents live in one container, discriminated by the `type` field:

| `type` | Description | Count |
|---|---|---|
| `team` | One per FIFA WC2026 team (48 total) | 48 |
| `participant` | Pool participant with their 5 assigned teams | 5 |
| `match` | Group-stage and knockout fixtures | 72+ |
| `simulationRun` | Latest cached Monte Carlo result | 1 |
| `auditLog` | Admin override audit trail | varies |

Indexing is scoped to `/type/?`, `/status/?`, `/round/?`, `/group/?`, and `/matchesCompletedAtRun/?`; everything else is excluded to minimize RU consumption.

### Azure Static Web App

- **Plan**: Free tier
- **Build**: `pnpm build` produces a static export under `web/out/`
- **Routing**: all navigations are client-side; the SWA serves the pre-rendered HTML shells

During the tournament the frontend called the API via `NEXT_PUBLIC_API_BASE_URL`, baked into the static bundle at build time. Post-archive it fetches the `/data/*.json` snapshots instead and the variable is gone.

---

## Data Flow

### Match result sync (timer trigger, every 2 hours)

```
TheSportsDB API
  └─► handlers/sync.py
        ├─ Fetch live + scheduled events for league 4429
        ├─ For each event:
        │    ├─ Resolve home/away team IDs from name map
        │    ├─ If score changed: patch match in Cosmos + update Elo ratings
        │    └─ If new match: upsert match document
        └─ Write audit log entry
```

Elo ratings are updated in Cosmos after each completed match. The sync handler reads the current Elo from Cosmos, applies the standard formula (K=32), and patches both team documents atomically.

### Standings request

```
GET /api/standings
  └─► handlers/standings.py
        ├─ Query all matches + participants + teams from Cosmos
        │    (falls back to shared/seed/ if Cosmos is empty)
        ├─ api/scoring.py:compute_scores(matches, participants, teams)
        │    ├─ +1 pt per team that appears in any r32 fixture (group qualification)
        │    └─ +N pts per knockout win (r32=2, r16=3, qf=5, sf=8, final=13)
        └─ Return ranked list with participant, score, and team details
```

### Simulation request

```
POST /api/simulate  { overrides: [...], nRuns: 10000 }
  └─► handlers/simulate.py
        ├─ Validate input (overrides: list, nRuns: 1–100000)
        ├─ Count completed matches (cache key)
        ├─ If no overrides AND cached doc matches completed count:
        │    └─ Return cached simulationRun document
        ├─ Load matches + participants + teams (Cosmos → seed fallback)
        ├─ Apply overrides to in-memory match list
        ├─ simulation/engine.py:run_simulation(...)
        │    └─ (see docs/simulation.md)
        ├─ If no overrides: upsert simulationRun_latest to Cosmos
        └─ Return SimulationRun JSON
```

---

## Data Models

Defined in `api/models/` as Pydantic v2 models with camelCase alias generation. The same camelCase field names are used by the TypeScript types in `web/lib/types.ts`.

```python
class Team(BaseModel):
    id: str            # FIFA team code, e.g. "MEX"
    name: str
    group: str         # "A"–"L"
    elo_rating: float  # Current Elo (updated after each completed match)
    status: TeamStatus # active | eliminated | qualified | champion

class Participant(BaseModel):
    id: str            # lowercase first name, e.g. "ricardo"
    display_name: str
    team_ids: list[str]  # exactly 5 team IDs

class Match(BaseModel):
    id: str
    round: MatchRound  # group | r32 | r16 | qf | sf | final
    home_team_id: str
    away_team_id: str
    scheduled_at: datetime
    home_score: int | None
    away_score: int | None
    winner_id: str | None
    status: MatchStatus  # scheduled | live | completed

class SimulationRun(BaseModel):
    id: str                          # always "simulationRun_latest"
    run_at: datetime
    matches_completed_at_run: int
    n_runs: int
    win_probabilities: dict[str, float]  # participant_id → probability of winning
```

---

## Repository Structure

```
wc26-dashboard/
├── .github/
│   ├── actions/          Reusable composite actions
│   │   ├── ci-api/       Lint + typecheck + test (Python)
│   │   ├── ci-frontend/  Type-check + lint (TypeScript)
│   │   ├── ci-e2e/       Cypress smoke suite
│   │   ├── smoke-api/    Post-deploy API health check
│   │   └── smoke-web/    Post-deploy web health check
│   └── workflows/
│       ├── ci.yml        PR checks (api + frontend + e2e)
│       └── deploy-site.yml  Static site deploy to SWA (post-archive)
├── api/
│   ├── handlers/         One module per endpoint
│   ├── models/           Pydantic models
│   ├── simulation/       Monte Carlo engine (engine.py) + bracket (bracket.py)
│   ├── tests/            pytest suite (138 tests)
│   └── cors.py / cosmos.py / scoring.py / seed.py
├── docs/                 This folder
├── infra/
│   ├── *.tf              Terraform resources
│   └── arm/              ARM template for FC1 Function App (provider workaround)
├── scripts/              One-off and maintenance scripts
├── shared/seed/          Static seed data (participants, teams, fixtures)
├── web/
│   ├── app/              Next.js App Router pages
│   ├── components/       React components
│   ├── lib/              API client, types, translations, constants
│   └── public/data/      Final tournament data (the static archive)
├── docker-compose.yml
├── function_app.py       Azure Functions entry point
└── pyproject.toml        Python project config + tox setup
```
