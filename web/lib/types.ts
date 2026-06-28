export type TeamStatus = "active" | "eliminated" | "champion" | "qualified";
export type MatchStatus = "scheduled" | "live" | "completed";
export type MatchRound = "group" | "r32" | "r16" | "qf" | "sf" | "final";

export interface Team {
  id: string;
  name: string;
  group: string;
  eloRating: number;
  status: TeamStatus;
}

export interface Participant {
  id: string;
  displayName: string;
  teamIds: string[];
}

export interface Match {
  id: string;
  round: MatchRound;
  homeTeamId: string;
  awayTeamId: string;
  scheduledAt: string;
  venue: string;
  homeScore: number | null;
  awayScore: number | null;
  winnerId: string | null;
  status: MatchStatus;
}

export interface SimulationRun {
  id: string;
  runAt: string;
  matchesCompletedAtRun: number;
  nRuns: number;
  winProbabilities: Record<string, number>;
  teamWinProbabilities?: Record<string, number>;
}

export interface StandingsEntry {
  participant: Participant;
  score: number;
  teams: Team[];
}
