"use client";

import Image from "next/image";
import type { ApiMatch } from "@/lib/api";
import { FIFA_TO_ISO2 } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/locale-context";

type Round = "r32" | "r16" | "qf" | "sf" | "final";

export interface BracketMatchesByRound {
  r32: ApiMatch[];
  r16: ApiMatch[];
  qf: ApiMatch[];
  sf: ApiMatch[];
  final: ApiMatch[];
}

const ROUND_ORDER: Round[] = ["r32", "r16", "qf", "sf", "final"];

const ROUND_LABELS: Record<Round, string> = {
  r32: "Round of 32",
  r16: "Round of 16",
  qf: "Quarterfinals",
  sf: "Semifinals",
  final: "Final",
};

// Vertical height (px) for one R32 match slot. All other rounds scale from this.
const SLOT_HEIGHT = 96;
// Total bracket height = 16 R32 slots
const BRACKET_HEIGHT = 16 * SLOT_HEIGHT;

function TeamRow({
  teamId,
  name,
  isWinner,
  tbd,
}: {
  teamId: string | null;
  name: string | null;
  isWinner: boolean;
  tbd: string;
}) {
  const iso2 = teamId ? (FIFA_TO_ISO2[teamId] ?? null) : null;
  return (
    <div
      className={cn(
        "flex items-center gap-2 px-2 py-1.5 text-xs",
        isWinner ? "bg-green-50 font-semibold text-green-900" : "text-gray-700"
      )}
    >
      <span className="shrink-0 w-6 h-[18px] inline-flex items-center">
        {iso2 ? (
          <Image
            src={`https://flagcdn.com/24x18/${iso2}.png`}
            width={24}
            height={18}
            alt={name ?? ""}
            className="rounded-[2px] object-cover"
            unoptimized
          />
        ) : (
          <span className="w-6 h-[18px] rounded-[2px] bg-gray-200 inline-block" />
        )}
      </span>
      <span className="truncate max-w-[80px]">{name ?? tbd}</span>
    </div>
  );
}

function MatchCard({ match, tbd }: { match: ApiMatch; tbd: string }) {
  const isLive = match.status === "live";
  const isCompleted = match.status === "completed";
  const homeWon = match.winnerId === match.homeTeam?.id;
  const awayWon = match.winnerId === match.awayTeam?.id;

  return (
    <div className="w-44 rounded-lg border bg-white shadow-sm overflow-hidden shrink-0">
      <TeamRow
        teamId={match.homeTeam?.id ?? null}
        name={match.homeTeam?.name ?? null}
        isWinner={homeWon}
        tbd={tbd}
      />
      <div className="border-t border-b flex items-center justify-center gap-3 py-0.5 px-2">
        {isCompleted && (
          <span className="text-[11px] font-mono text-gray-500">
            {match.homeScore} – {match.awayScore}
          </span>
        )}
        {isLive && (
          <span className="text-[10px] font-semibold text-red-500 uppercase tracking-wide">
            Live
          </span>
        )}
        {!isCompleted && !isLive && (
          <span className="text-[10px] text-gray-300">vs</span>
        )}
      </div>
      <TeamRow
        teamId={match.awayTeam?.id ?? null}
        name={match.awayTeam?.name ?? null}
        isWinner={awayWon}
        tbd={tbd}
      />
    </div>
  );
}

function PlaceholderCard({ tbd }: { tbd: string }) {
  return (
    <div className="w-44 rounded-lg border border-dashed border-gray-200 bg-gray-50 overflow-hidden shrink-0">
      <div className="flex items-center gap-2 px-2 py-1.5">
        <span className="w-6 h-[18px] rounded-[2px] bg-gray-200 shrink-0 inline-block" />
        <span className="text-xs text-gray-400">{tbd}</span>
      </div>
      <div className="border-t border-b py-0.5 px-2">
        <span className="text-[10px] text-gray-300">vs</span>
      </div>
      <div className="flex items-center gap-2 px-2 py-1.5">
        <span className="w-6 h-[18px] rounded-[2px] bg-gray-200 shrink-0 inline-block" />
        <span className="text-xs text-gray-400">{tbd}</span>
      </div>
    </div>
  );
}

function RoundColumn({
  round,
  matches,
  expectedCount,
  tbd,
}: {
  round: Round;
  matches: ApiMatch[];
  expectedCount: number;
  tbd: string;
}) {
  // Fill to expectedCount with placeholders so spacing stays correct
  const slots = Array.from({ length: expectedCount }, (_, i) => matches[i] ?? null);

  return (
    <div className="flex flex-col shrink-0" style={{ height: BRACKET_HEIGHT }}>
      <p className="mb-2 text-center text-[10px] font-semibold uppercase tracking-widest text-gray-400 shrink-0">
        {ROUND_LABELS[round]}
      </p>
      <div
        className="flex flex-col flex-1"
        style={{ justifyContent: "space-around" }}
      >
        {slots.map((match, i) =>
          match ? (
            <MatchCard key={match.id} match={match} tbd={tbd} />
          ) : (
            <PlaceholderCard key={i} tbd={tbd} />
          )
        )}
      </div>
    </div>
  );
}

const EXPECTED_COUNTS: Record<Round, number> = {
  r32: 16,
  r16: 8,
  qf: 4,
  sf: 2,
  final: 1,
};

export function BracketTree({ matchesByRound }: { matchesByRound: BracketMatchesByRound }) {
  const t = useT();
  const tbd = t("bracket.tbd");

  return (
    <div className="flex gap-6 items-start pb-4" style={{ minHeight: BRACKET_HEIGHT + 32 }}>
      {ROUND_ORDER.map((round) => (
        <RoundColumn
          key={round}
          round={round}
          matches={matchesByRound[round]}
          expectedCount={EXPECTED_COUNTS[round]}
          tbd={tbd}
        />
      ))}
    </div>
  );
}
