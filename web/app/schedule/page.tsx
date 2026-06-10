"use client";

import { useState, useMemo } from "react";
import { MATCHES, TEAMS, ROUND_LABELS, getTeamOwner, PARTICIPANT_COLORS } from "@/lib/mock-data";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { MatchRound } from "@/lib/types";

const ROUNDS: { value: "all" | MatchRound; label: string }[] = [
  { value: "all", label: "All Rounds" },
  { value: "group", label: "Group Stage" },
  { value: "r32", label: "Round of 32" },
  { value: "r16", label: "Round of 16" },
  { value: "qf", label: "Quarterfinal" },
  { value: "sf", label: "Semifinal" },
  { value: "final", label: "Final" },
];

const teamsById = Object.fromEntries(TEAMS.map((t) => [t.id, t]));

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
}

function formatTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZoneName: "short" });
}

function groupMatchesByDate(matches: typeof MATCHES) {
  const groups = new Map<string, typeof MATCHES>();
  for (const match of matches) {
    const dateKey = new Date(match.scheduledAt).toDateString();
    if (!groups.has(dateKey)) groups.set(dateKey, []);
    groups.get(dateKey)!.push(match);
  }
  return groups;
}

export default function SchedulePage() {
  const [selectedRound, setSelectedRound] = useState<"all" | MatchRound>("all");

  const filtered = useMemo(() => {
    if (selectedRound === "all") return MATCHES;
    return MATCHES.filter((m) => m.round === selectedRound);
  }, [selectedRound]);

  const grouped = useMemo(() => groupMatchesByDate(filtered), [filtered]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900">Schedule</h1>
      <p className="mt-1 text-sm text-gray-500">Match schedule with participant team highlights.</p>

      {/* Desktop filter bar */}
      <div className="mt-6 hidden md:flex items-center gap-3 rounded-lg bg-gray-100 px-4 py-3">
        <Select value={selectedRound} onValueChange={(v) => setSelectedRound(v as "all" | MatchRound)}>
          <SelectTrigger className="w-44 bg-white">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ROUNDS.map((r) => (
              <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={() => setSelectedRound("all")}>
          All
        </Button>
      </div>

      {/* Mobile chip row */}
      <div className="mt-4 flex overflow-x-auto gap-2 pb-1 md:hidden">
        {ROUNDS.map((r) => (
          <Button
            key={r.value}
            variant={selectedRound === r.value ? "default" : "outline"}
            size="sm"
            className="whitespace-nowrap flex-shrink-0"
            onClick={() => setSelectedRound(r.value)}
          >
            {r.label}
          </Button>
        ))}
      </div>

      {/* Match list */}
      <div className="mt-6 space-y-6">
        {[...grouped.entries()].map(([dateKey, matches]) => (
          <div key={dateKey}>
            <p className="text-sm text-gray-500 font-medium mb-2">
              {formatDate(matches[0].scheduledAt)}
            </p>
            <div className="space-y-3">
              {matches.map((match) => {
                const home = teamsById[match.homeTeamId];
                const away = teamsById[match.awayTeamId];
                const homeOwner = getTeamOwner(match.homeTeamId);
                const awayOwner = getTeamOwner(match.awayTeamId);
                const ownerColor =
                  homeOwner ? PARTICIPANT_COLORS[homeOwner.id] :
                  awayOwner ? PARTICIPANT_COLORS[awayOwner.id] : undefined;

                return (
                  <Card
                    key={match.id}
                    className="overflow-hidden border"
                    style={ownerColor ? { borderLeft: `4px solid ${ownerColor}` } : undefined}
                  >
                    <CardContent className="p-4">
                      {/* Desktop layout */}
                      <div className="hidden md:flex items-center gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 text-sm font-semibold">
                            <span className="font-mono bg-gray-100 px-1.5 rounded text-xs">{home?.id}</span>
                            <span>{home?.name}</span>
                            <span className="text-gray-400 mx-1">vs</span>
                            <span>{away?.name}</span>
                            <span className="font-mono bg-gray-100 px-1.5 rounded text-xs">{away?.id}</span>
                          </div>
                          <div className="mt-1 text-xs text-gray-400">
                            {formatDate(match.scheduledAt)} · {formatTime(match.scheduledAt)} · {match.venue}
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          {match.homeScore !== null && (
                            <span className="font-bold text-gray-900 text-lg">
                              {match.homeScore}–{match.awayScore}
                            </span>
                          )}
                          <StatusBadge status={match.status} />
                        </div>
                        <div className="text-xs text-gray-400 text-right min-w-[80px]">
                          {ROUND_LABELS[match.round]}
                        </div>
                      </div>

                      {/* Mobile layout */}
                      <div className="md:hidden">
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="text-sm font-semibold">
                              {home?.name} <span className="text-gray-400">vs</span> {away?.name}
                            </p>
                            <p className="text-xs text-gray-400 mt-0.5">
                              {formatDate(match.scheduledAt)} · {match.venue}
                            </p>
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <StatusBadge status={match.status} />
                            {match.homeScore !== null && (
                              <span className="font-bold text-sm">
                                {match.homeScore}–{match.awayScore}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        ))}

        {filtered.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-12">No matches found for this filter.</p>
        )}
      </div>
    </div>
  );
}
