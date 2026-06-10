"use client";

import { useState, useMemo, useEffect } from "react";
import { getMatches, getStandings, type ApiMatch } from "@/lib/api";
import { PARTICIPANT_COLORS } from "@/lib/mock-data";
import type { StandingsEntry } from "@/lib/types";
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
import { useT, useLocale } from "@/lib/locale-context";
import { PageSkeleton } from "@/components/page-skeleton";

const ROUND_VALUES: Array<"all" | MatchRound> = ["all", "group", "r32", "r16", "qf", "sf", "final"];

function groupMatchesByDate(matches: ApiMatch[]) {
  const groups = new Map<string, ApiMatch[]>();
  for (const match of matches) {
    const dateKey = new Date(match.scheduledAt).toDateString();
    if (!groups.has(dateKey)) groups.set(dateKey, []);
    groups.get(dateKey)!.push(match);
  }
  return groups;
}

function buildOwnerMap(standings: StandingsEntry[]): Record<string, string> {
  const map: Record<string, string> = {};
  for (const entry of standings) {
    for (const teamId of entry.participant.teamIds) {
      map[teamId] = entry.participant.id;
    }
  }
  return map;
}

export default function SchedulePage() {
  const [selectedRound, setSelectedRound] = useState<"all" | MatchRound>("all");
  const [matches, setMatches] = useState<ApiMatch[] | null>(null);
  const [standings, setStandings] = useState<StandingsEntry[]>([]);
  const [error, setError] = useState(false);
  const t = useT();
  const { locale } = useLocale();
  const dateLocale = locale === "es" ? "es-MX" : "en-US";

  useEffect(() => {
    Promise.all([getMatches(), getStandings()])
      .then(([m, s]) => {
        setMatches(m);
        setStandings(s);
      })
      .catch(() => setError(true));
  }, []);

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString(dateLocale, {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function formatTime(iso: string) {
    return new Date(iso).toLocaleTimeString(dateLocale, {
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short",
    });
  }

  const ownerMap = useMemo(() => buildOwnerMap(standings), [standings]);

  const filtered = useMemo(() => {
    if (!matches) return [];
    if (selectedRound === "all") return matches;
    return matches.filter((m) => m.round === selectedRound);
  }, [matches, selectedRound]);

  const grouped = useMemo(() => groupMatchesByDate(filtered), [filtered]);

  const roundLabel = (r: "all" | MatchRound) =>
    r === "all" ? t("schedule.allRounds") : t(`rounds.${r}`);

  if (!matches && !error) {
    return <PageSkeleton />;
  }
  if (error) {
    return <p className="mx-auto max-w-4xl px-4 py-16 text-sm text-red-500">{t("schedule.error")}</p>;
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900">{t("schedule.title")}</h1>
      <p className="mt-1 text-sm text-gray-500">{t("schedule.subtitle")}</p>

      {/* Desktop filter bar */}
      <div className="mt-6 hidden md:flex items-center gap-3 rounded-lg bg-gray-100 px-4 py-3">
        <Select value={selectedRound} onValueChange={(v) => setSelectedRound(v as "all" | MatchRound)}>
          <SelectTrigger className="w-44 bg-white">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ROUND_VALUES.map((r) => (
              <SelectItem key={r} value={r}>{roundLabel(r)}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={() => setSelectedRound("all")}>
          {t("schedule.allRounds")}
        </Button>
      </div>

      {/* Mobile chip row */}
      <div className="mt-4 flex overflow-x-auto gap-2 pb-1 md:hidden">
        {ROUND_VALUES.map((r) => (
          <Button
            key={r}
            variant={selectedRound === r ? "default" : "outline"}
            size="sm"
            className="whitespace-nowrap shrink-0"
            onClick={() => setSelectedRound(r)}
          >
            {roundLabel(r)}
          </Button>
        ))}
      </div>

      {/* Match list */}
      <div className="mt-6 space-y-6">
        {[...grouped.entries()].map(([dateKey, dayMatches]) => (
          <div key={dateKey}>
            <p className="text-sm text-gray-500 font-medium mb-2">
              {formatDate(dayMatches[0].scheduledAt)}
            </p>
            <div className="space-y-3">
              {dayMatches.map((match) => {
                const homeOwnerId = ownerMap[match.homeTeam.id];
                const awayOwnerId = ownerMap[match.awayTeam.id];
                const ownerColor =
                  homeOwnerId ? PARTICIPANT_COLORS[homeOwnerId] :
                  awayOwnerId ? PARTICIPANT_COLORS[awayOwnerId] : undefined;

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
                            <span className="font-mono bg-gray-100 px-1.5 rounded text-xs">{match.homeTeam.id}</span>
                            <span>{match.homeTeam.name}</span>
                            <span className="text-gray-400 mx-1">vs</span>
                            <span>{match.awayTeam.name}</span>
                            <span className="font-mono bg-gray-100 px-1.5 rounded text-xs">{match.awayTeam.id}</span>
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
                        <div className="text-xs text-gray-400 text-right min-w-20">
                          {t(`rounds.${match.round}`)}
                        </div>
                      </div>

                      {/* Mobile layout */}
                      <div className="md:hidden">
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="text-sm font-semibold">
                              {match.homeTeam.name} <span className="text-gray-400">vs</span> {match.awayTeam.name}
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
          <p className="text-sm text-gray-400 text-center py-12">{t("schedule.noMatches")}</p>
        )}
      </div>
    </div>
  );
}
