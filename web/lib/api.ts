import type { MatchRound, SimulationRun, StandingsEntry, TeamStatus } from "./types";

const VALID_TEAM_STATUSES: ReadonlySet<TeamStatus> = new Set([
  "active",
  "eliminated",
  "qualified",
  "champion",
]);
function toTeamStatus(raw: string): TeamStatus {
  return VALID_TEAM_STATUSES.has(raw as TeamStatus) ? (raw as TeamStatus) : "active";
}

// ── In-memory TTL cache with in-flight deduplication ────────────────────────

const _cache = new Map<string, { data: unknown; expiresAt: number }>();
const _inflight = new Map<string, Promise<unknown>>();

function cached<T>(key: string, ttlMs: number, fetcher: () => Promise<T>): Promise<T> {
  const hit = _cache.get(key);
  if (hit && hit.expiresAt > Date.now()) {
    return Promise.resolve(hit.data as T);
  }
  const existing = _inflight.get(key);
  if (existing) return existing as Promise<T>;
  const promise = fetcher().then((data) => {
    _cache.set(key, { data, expiresAt: Date.now() + ttlMs });
    _inflight.delete(key);
    return data;
  });
  _inflight.set(key, promise as Promise<unknown>);
  return promise;
}

// ── Raw API response shapes ─────────────────────────────────────────────────

interface ApiTeamRef {
  id: string;
  name: string;
  eloRating: number | null;
}

interface ApiStandingTeam {
  teamId: string;
  name: string;
  group: string | null;
  status: string;
  eloRating: number | null;
}

interface ApiStandingEntry {
  rank: number;
  participantId: string;
  displayName: string;
  score: number;
  teams: ApiStandingTeam[];
}

export interface ApiMatch {
  id: string;
  round: MatchRound;
  group: string | null;
  homeTeam: ApiTeamRef;
  awayTeam: ApiTeamRef;
  scheduledAt: string;
  venue: string;
  homeScore: number | null;
  awayScore: number | null;
  winnerId: string | null;
  status: "scheduled" | "live" | "completed";
}

// ── Adapters ────────────────────────────────────────────────────────────────

function toStandingsEntry(entry: ApiStandingEntry): StandingsEntry {
  return {
    participant: {
      id: entry.participantId,
      displayName: entry.displayName,
      teamIds: entry.teams.map((t) => t.teamId),
    },
    score: entry.score,
    teams: entry.teams.map((t) => ({
      id: t.teamId,
      name: t.name,
      group: t.group ?? "",
      eloRating: t.eloRating ?? 0,
      status: toTeamStatus(t.status),
    })),
  };
}

// ── Public fetch functions ──────────────────────────────────────────────────
//
// The tournament is over: the live Azure Functions API has been retired and
// the final data is baked into the site as static JSON snapshots under
// /public/data/. Same response shapes as the old API.

export async function getStandings(): Promise<StandingsEntry[]> {
  return cached("standings", 60_000, async () => {
    const res = await fetch("/data/standings.json");
    if (!res.ok) throw new Error(`standings: ${res.status}`);
    const data = (await res.json()) as { standings: ApiStandingEntry[] };
    return data.standings.map(toStandingsEntry);
  });
}

export async function getMatches(): Promise<ApiMatch[]> {
  return cached("matches", 60_000, async () => {
    const res = await fetch("/data/matches.json");
    if (!res.ok) throw new Error(`matches: ${res.status}`);
    const data = (await res.json()) as { matches: ApiMatch[] };
    return data.matches;
  });
}

export async function getSimulation(overrides?: object[]): Promise<SimulationRun> {
  // ponytail: overrides ignored; with every match completed the scenario
  // builder is unreachable, and the archive always serves the final run.
  void overrides;
  const res = await fetch("/data/simulation.json");
  if (!res.ok) throw new Error(`simulate: ${res.status}`);
  return res.json() as Promise<SimulationRun>;
}
