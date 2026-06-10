"use client";

import { useState, useMemo, useEffect } from "react";
import { getStandings } from "@/lib/api";
import { PARTICIPANT_COLORS } from "@/lib/mock-data";
import type { StandingsEntry, TeamStatus } from "@/lib/types";
import { ParticipantBadge } from "@/components/participant-badge";
import { TeamRow } from "@/components/team-badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { useT } from "@/lib/locale-context";

type SortKey = "participant" | "name" | "score";
type StatusFilter = "all" | TeamStatus;

const STATUS_VALUES: StatusFilter[] = ["all", "active", "qualified", "champion", "eliminated"];

export default function TeamsPage() {
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [standings, setStandings] = useState<StandingsEntry[] | null>(null);
  const [error, setError] = useState(false);
  const t = useT();

  useEffect(() => {
    getStandings().then(setStandings).catch(() => setError(true));
  }, []);

  const sortedStandings = useMemo(() => {
    if (!standings) return [];
    const entries = [...standings];
    if (sortKey === "score") entries.sort((a, b) => b.score - a.score);
    else if (sortKey === "name") entries.sort((a, b) => a.participant.displayName.localeCompare(b.participant.displayName));
    return entries;
  }, [standings, sortKey]);

  const statusLabel = (f: StatusFilter) =>
    f === "all" ? t("teams.statusAll") : t(`status.${f}`);

  if (!standings && !error) {
    return <p className="mx-auto max-w-5xl px-4 py-16 text-sm text-gray-500">{t("teams.loading")}</p>;
  }
  if (error) {
    return <p className="mx-auto max-w-5xl px-4 py-16 text-sm text-red-500">{t("teams.error")}</p>;
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900">{t("teams.title")}</h1>
      <p className="mt-1 text-sm text-gray-500">{t("teams.subtitle")}</p>

      {/* Desktop filter bar */}
      <div className="mt-6 hidden md:flex items-center gap-3 rounded-lg bg-gray-100 px-4 py-3">
        <Select value={sortKey} onValueChange={(v) => setSortKey(v as SortKey)}>
          <SelectTrigger className="w-44 bg-white">
            <SelectValue placeholder={t("teams.sortByScore")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="score">{t("teams.sortByScore")}</SelectItem>
            <SelectItem value="participant">{t("teams.sortByParticipant")}</SelectItem>
            <SelectItem value="name">{t("teams.sortByName")}</SelectItem>
          </SelectContent>
        </Select>
        <div className="flex gap-2">
          {STATUS_VALUES.map((f) => (
            <Button
              key={f}
              variant={statusFilter === f ? "default" : "outline"}
              size="sm"
              onClick={() => setStatusFilter(f)}
            >
              {statusLabel(f)}
            </Button>
          ))}
        </div>
      </div>

      {/* Mobile chip row */}
      <div className="mt-4 flex overflow-x-auto gap-2 pb-1 md:hidden">
        {STATUS_VALUES.map((f) => (
          <Button
            key={f}
            variant={statusFilter === f ? "default" : "outline"}
            size="sm"
            className="whitespace-nowrap shrink-0"
            onClick={() => setStatusFilter(f)}
          >
            {statusLabel(f)}
          </Button>
        ))}
      </div>

      {/* Desktop grid */}
      <div className="mt-6 hidden md:grid grid-cols-2 gap-6">
        {sortedStandings.map((entry) => {
          const color = PARTICIPANT_COLORS[entry.participant.id] ?? "#6B7280";
          const filteredTeams = statusFilter === "all"
            ? entry.teams
            : entry.teams.filter((t) => t.status === statusFilter);

          return (
            <Card
              key={entry.participant.id}
              className="overflow-hidden border-t-4"
              style={{ borderTopColor: color }}
            >
              <CardHeader className="pb-2 pt-4 px-4 flex flex-row items-center justify-between">
                <ParticipantBadge
                  participantId={entry.participant.id}
                  displayName={entry.participant.displayName}
                  className="text-base shrink-0"
                />
                <span
                  className="inline-flex items-center justify-center rounded-full px-3 py-0.5 text-sm font-bold text-white"
                  style={{ backgroundColor: color }}
                >
                  {entry.score} {t("teams.pts")}
                </span>
              </CardHeader>
              <CardContent className="px-4 pb-4 divide-y">
                {filteredTeams.length === 0 ? (
                  <p className="text-sm text-gray-400 py-2">{t("teams.noTeamsFilter")}</p>
                ) : (
                  filteredTeams.map((team) => (
                    <TeamRow key={team.id} team={team} />
                  ))
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Mobile accordion */}
      <Accordion multiple defaultValue={sortedStandings.map((e) => e.participant.id)} className="mt-6 md:hidden space-y-3">
        {sortedStandings.map((entry) => {
          const color = PARTICIPANT_COLORS[entry.participant.id] ?? "#6B7280";
          const filteredTeams = statusFilter === "all"
            ? entry.teams
            : entry.teams.filter((t) => t.status === statusFilter);

          return (
            <AccordionItem
              key={entry.participant.id}
              value={entry.participant.id}
              className="rounded-lg border bg-white shadow-sm overflow-hidden"
              style={{ borderLeft: `4px solid ${color}` }}
            >
              <AccordionTrigger className="px-4 py-3">
                <div className="flex items-center w-full gap-3">
                  <ParticipantBadge
                    participantId={entry.participant.id}
                    displayName={entry.participant.displayName}
                  />
                  <span className="ml-auto mr-2 text-sm font-semibold text-gray-600">
                    {entry.score} {t("teams.pts")}
                  </span>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-4 pb-3 divide-y">
                {filteredTeams.length === 0 ? (
                  <p className="text-sm text-gray-400 py-2">{t("teams.noTeamsFilter")}</p>
                ) : (
                  filteredTeams.map((team) => (
                    <TeamRow key={team.id} team={team} />
                  ))
                )}
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>
    </div>
  );
}
