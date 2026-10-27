"use client";

import { useEffect, useState } from "react";
import { getStandings } from "@/lib/api";
import { PARTICIPANT_COLORS } from "@/lib/constants";
import type { StandingsEntry, TeamStatus } from "@/lib/types";
import { ParticipantBadge } from "@/components/participant-badge";
import { StatusBadge } from "@/components/status-badge";
import { TeamPill } from "@/components/team-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { useT } from "@/lib/locale-context";
import { PageSkeleton } from "@/components/page-skeleton";

function participantStatus(teams: StandingsEntry["teams"]): TeamStatus {
  if (teams.some((t) => t.status === "champion")) return "champion";
  if (teams.every((t) => t.status === "eliminated")) return "eliminated";
  return "active";
}

const SCORING_MILESTONE_KEYS = [
  { key: "groupQualification", pts: 1 },
  { key: "round32win", pts: 2 },
  { key: "round16win", pts: 3 },
  { key: "quarterfinalWin", pts: 5 },
  { key: "semifinalWin", pts: 8 },
  { key: "championshipWin", pts: 13 },
] as const;

export default function StandingsPage() {
  const [standings, setStandings] = useState<StandingsEntry[] | null>(null);
  const [error, setError] = useState(false);
  const t = useT();

  useEffect(() => {
    getStandings().then(setStandings).catch(() => setError(true));
  }, []);

  if (!standings && !error) {
    return <PageSkeleton />;
  }
  if (error) {
    return <p className="mx-auto max-w-5xl px-4 py-16 text-sm text-red-500">{t("standings.error")}</p>;
  }

  const winner = standings![0];
  const championTeam = winner?.teams.find((tm) => tm.status === "champion");

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900" data-cy="standings-heading">{t("standings.title")}</h1>
      <p className="mt-1 text-sm text-gray-500">{t("standings.subtitle")}</p>

      {/* Champion banner */}
      {winner && (
        <div
          className="mt-6 rounded-lg border border-amber-300 bg-gradient-to-r from-amber-50 via-yellow-50 to-amber-50 px-6 py-8 text-center shadow-sm"
          data-cy="champion-banner"
        >
          <div className="text-5xl">🏆</div>
          <h2 className="mt-3 text-2xl font-bold text-gray-900">
            {winner.participant.displayName} · {t("standings.championBanner")}
          </h2>
          <p className="mt-1 text-sm font-semibold text-amber-700">
            {winner.score} {t("teams.pts")}
          </p>
          {championTeam && (
            <p className="mt-2 text-sm text-gray-600">
              ⚽ {championTeam.name} · {t("standings.worldChampion")}
            </p>
          )}
        </div>
      )}

      {/* Desktop table */}
      <div className="mt-6 hidden md:block rounded-lg border bg-white shadow-sm overflow-hidden" data-cy="standings-table">
        <Table>
          <TableHeader>
            <TableRow className="bg-[#F3F4F6]">
              <TableHead className="w-12 text-center font-semibold text-gray-700">{t("standings.rank")}</TableHead>
              <TableHead className="font-semibold text-gray-700">{t("standings.participant")}</TableHead>
              <TableHead className="w-24 text-center font-semibold text-gray-700">{t("standings.score")}</TableHead>
              <TableHead className="font-semibold text-gray-700">{t("standings.teams")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {standings!.map((entry, i) => {
              const color = PARTICIPANT_COLORS[entry.participant.id] ?? "#6B7280";
              const ps = participantStatus(entry.teams);
              return (
                <TableRow
                  key={entry.participant.id}
                  className={`${i % 2 === 0 ? "bg-white" : "bg-gray-50"} ${ps === "eliminated" ? "opacity-40" : ""}`}
                >
                  <TableCell className="text-center text-sm font-semibold text-gray-500">
                    {i + 1}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <ParticipantBadge
                        participantId={entry.participant.id}
                        displayName={entry.participant.displayName}
                      />
                      {ps !== "active" && <StatusBadge status={ps} />}
                    </div>
                  </TableCell>
                  <TableCell className="text-center">
                    <span
                      className="inline-flex items-center justify-center rounded-full px-3 py-0.5 text-sm font-bold text-white"
                      style={{ backgroundColor: color }}
                    >
                      {entry.score}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1.5">
                      {entry.teams.map((team) => (
                        <TeamPill key={team.id} team={team} showStatus={false} />
                      ))}
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* Mobile cards */}
      <div className="mt-6 flex flex-col gap-3 md:hidden">
        {standings!.map((entry, i) => {
          const color = PARTICIPANT_COLORS[entry.participant.id] ?? "#6B7280";
          const ps = participantStatus(entry.teams);
          return (
            <div
              key={entry.participant.id}
              className={`rounded-lg border bg-white shadow-sm overflow-hidden ${ps === "eliminated" ? "opacity-40" : ""}`}
              style={{ borderLeft: `4px solid ${color}` }}
            >
              <Accordion>
                <AccordionItem value="teams">
                  <AccordionTrigger className="px-4 py-3">
                    <div className="flex items-center gap-3 w-full">
                      <span className="text-sm font-semibold text-gray-400 w-5 text-center">
                        #{i + 1}
                      </span>
                      <ParticipantBadge
                        participantId={entry.participant.id}
                        displayName={entry.participant.displayName}
                      />
                      {ps !== "active" && <StatusBadge status={ps} />}
                      <span
                        className="ml-auto mr-2 inline-flex items-center justify-center rounded-full px-3 py-0.5 text-sm font-bold text-white"
                        style={{ backgroundColor: color }}
                      >
                        {entry.score}
                      </span>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-3">
                    <div className="grid grid-cols-2 gap-1.5">
                      {entry.teams.map((team) => (
                        <div key={team.id} className="flex items-center gap-1.5">
                          <span className="font-mono text-[10px] font-bold text-gray-500 w-8">
                            {team.id}
                          </span>
                          <StatusBadge status={team.status} />
                        </div>
                      ))}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </div>
          );
        })}
      </div>

      {/* Scoring legend */}
      <div className="mt-8 rounded-lg border bg-white px-4 py-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-3">{t("standings.scoring")}</p>
        <div className="flex flex-wrap gap-x-6 gap-y-1">
          {SCORING_MILESTONE_KEYS.map((m) => (
            <div key={m.key} className="flex items-center gap-1.5 text-sm text-gray-600">
              <span className="font-bold text-gray-900">{m.pts}pt{m.pts > 1 ? "s" : ""}</span>
              <span>{t(`scoringMilestones.${m.key}`)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
