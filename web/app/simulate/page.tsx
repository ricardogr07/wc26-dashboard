"use client";

import { useEffect, useState } from "react";
import { getSimulation, getMatches, type ApiMatch } from "@/lib/api";
import { PARTICIPANT_COLORS } from "@/lib/mock-data";
import type { SimulationRun, MatchRound } from "@/lib/types";
import { ProbabilityChart } from "@/components/probability-chart";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RefreshCw, RotateCcw, Play, Sliders } from "lucide-react";
import { useT, useLocale } from "@/lib/locale-context";
import { cn } from "@/lib/utils";
import { PageSkeleton } from "@/components/page-skeleton";

const POSITIONS = ["1st", "2nd", "3rd", "4th", "5th"] as const;

const POSITION_COLORS = {
  "1st": "#F59E0B",
  "2nd": "#9CA3AF",
  "3rd": "#D97706",
  "4th": "#3B82F6",
  "5th": "#6B7280",
} as const;

const ROUND_ORDER: MatchRound[] = ["group", "r32", "r16", "qf", "sf", "final"];

type OverrideChoice = "home" | "away";

function pct(val: number) {
  return `${(val * 100).toFixed(1)}%`;
}

function buildOverrides(overrideMap: Map<string, OverrideChoice>, matches: ApiMatch[]) {
  return [...overrideMap.entries()].map(([matchId, choice]) => {
    const m = matches.find((x) => x.id === matchId)!;
    const winnerId = choice === "home" ? m.homeTeam.id : m.awayTeam.id;
    return {
      matchId,
      winnerId,
      homeScore: choice === "home" ? 1 : 0,
      awayScore: choice === "home" ? 0 : 1,
    };
  });
}

export default function SimulatePage() {
  const [simulation, setSimulation] = useState<SimulationRun | null>(null);
  const [error, setError] = useState(false);
  const [matches, setMatches] = useState<ApiMatch[]>([]);
  const [overrideMap, setOverrideMap] = useState<Map<string, OverrideChoice>>(new Map());
  const [scenarioSim, setScenarioSim] = useState<SimulationRun | null>(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);
  const [scenarioError, setScenarioError] = useState(false);
  const t = useT();
  const { locale } = useLocale();

  useEffect(() => {
    getSimulation().then(setSimulation).catch(() => setError(true));
    getMatches()
      .then((ms) => setMatches(ms.filter((m) => m.status !== "completed")))
      .catch(() => {});
  }, []);

  function handleOverride(matchId: string, choice: OverrideChoice) {
    setOverrideMap((prev) => {
      const next = new Map(prev);
      if (next.get(matchId) === choice) {
        next.delete(matchId);
      } else {
        next.set(matchId, choice);
      }
      return next;
    });
    setScenarioSim(null);
    setScenarioError(false);
  }

  async function runScenario() {
    if (overrideMap.size === 0) return;
    setScenarioLoading(true);
    setScenarioError(false);
    try {
      const overrides = buildOverrides(overrideMap, matches);
      const result = await getSimulation(overrides);
      setScenarioSim(result);
    } catch {
      setScenarioError(true);
    } finally {
      setScenarioLoading(false);
    }
  }

  function resetScenario() {
    setOverrideMap(new Map());
    setScenarioSim(null);
    setScenarioError(false);
  }

  function formatRunAt(iso: string) {
    return new Date(iso).toLocaleString(locale === "es" ? "es-MX" : "en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short",
    });
  }

  if (!simulation && !error) {
    return <PageSkeleton />;
  }
  if (error) {
    return (
      <p className="mx-auto max-w-5xl px-4 py-16 text-sm text-red-500">
        {t("simulate.error")}
      </p>
    );
  }

  const sim = simulation!;
  const participantNames = Object.fromEntries(
    Object.keys(sim.probabilities).map((id) => [
      id,
      id.charAt(0).toUpperCase() + id.slice(1),
    ])
  );
  const sortedEntries = Object.entries(sim.probabilities).sort(
    (a, b) => b[1]["1st"] - a[1]["1st"]
  );

  const matchesByRound = ROUND_ORDER.reduce<Record<string, ApiMatch[]>>((acc, round) => {
    const ms = matches.filter((m) => m.round === round);
    if (ms.length > 0) acc[round] = ms;
    return acc;
  }, {});

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* Metadata bar */}
      <div className="flex items-center gap-2 rounded-lg bg-gray-100 px-4 py-2.5 text-sm text-gray-500">
        <RefreshCw size={14} className="shrink-0" />
        <span>
          {t("simulate.lastRun")}{" "}
          <span className="font-medium text-gray-700">{formatRunAt(sim.runAt)}</span>
          <span className="mx-2">·</span>
          <span className="font-medium text-gray-700">{sim.nRuns.toLocaleString()}</span>{" "}
          {t("simulate.simulations")}
          <span className="mx-2">·</span>
          <span className="font-medium text-gray-700">{sim.matchesCompletedAtRun}</span>{" "}
          {t("simulate.matchesCompleted")}
        </span>
      </div>

      <h1 className="mt-6 text-2xl font-bold text-gray-900" data-cy="simulate-heading">{t("simulate.title")}</h1>
      <p className="mt-1 text-sm text-gray-500">{t("simulate.subtitle")}</p>

      {/* Probability chart */}
      <div className="mt-6 rounded-lg border bg-white shadow-sm p-4">
        <ProbabilityChart simulation={sim} participantNames={participantNames} />
      </div>

      {/* Baseline probability table */}
      <div className="mt-6 rounded-lg border bg-white shadow-sm overflow-hidden overflow-x-auto" data-cy="prob-table">
        <Table>
          <TableHeader>
            <TableRow className="bg-[#F3F4F6]">
              <TableHead className="font-semibold text-gray-700 sticky left-0 bg-[#F3F4F6]">
                {t("simulate.participant")}
              </TableHead>
              {POSITIONS.map((pos) => (
                <TableHead
                  key={pos}
                  className="text-center font-semibold"
                  style={{ color: POSITION_COLORS[pos] }}
                >
                  {t(`positions.${pos}`)}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedEntries.map(([id, probs], i) => {
              const color = PARTICIPANT_COLORS[id] ?? "#6B7280";
              const name = participantNames[id] ?? id;
              return (
                <TableRow key={id} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                  <TableCell className="font-medium sticky left-0 bg-inherit">
                    <div className="flex items-center gap-2">
                      <span
                        className="inline-block h-3 w-3 rounded-full shrink-0"
                        style={{ backgroundColor: color }}
                      />
                      {name}
                    </div>
                  </TableCell>
                  {POSITIONS.map((pos) => (
                    <TableCell key={pos} className="text-center text-sm font-mono">
                      {pct(probs[pos])}
                    </TableCell>
                  ))}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* Scenario Builder */}
      <Card className="mt-6">
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2 text-base">
                <Sliders size={16} />
                {t("simulate.scenarioBuilderTitle")}
              </CardTitle>
              <p className="mt-1 text-sm text-gray-500">{t("simulate.scenarioBuilderDesc")}</p>
            </div>
            {overrideMap.size > 0 && (
              <div className="flex shrink-0 items-center gap-2">
                <Button variant="outline" size="sm" onClick={resetScenario}>
                  <RotateCcw size={13} className="mr-1" />
                  {t("simulate.resetScenario")}
                </Button>
                <Button size="sm" onClick={runScenario} disabled={scenarioLoading}>
                  {scenarioLoading ? (
                    <RefreshCw size={13} className="mr-1 animate-spin" />
                  ) : (
                    <Play size={13} className="mr-1" />
                  )}
                  {t("simulate.runScenario")}
                </Button>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {matches.length === 0 ? (
            <p className="text-sm text-gray-400">{t("simulate.noFutureMatches")}</p>
          ) : (
            <div className="space-y-5">
              {Object.entries(matchesByRound).map(([round, roundMatches]) => (
                <div key={round}>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
                    {t(`rounds.${round as MatchRound}`)}
                  </p>
                  <div className="space-y-1.5">
                    {roundMatches.map((m) => {
                      const choice = overrideMap.get(m.id) ?? null;
                      return (
                        <div
                          key={m.id}
                          className="flex items-center justify-between rounded-md border bg-gray-50 px-3 py-2 text-sm"
                        >
                          <span className="flex-1 font-medium text-gray-700">
                            {m.homeTeam.name}{" "}
                            <span className="font-normal text-gray-400">vs</span>{" "}
                            {m.awayTeam.name}
                          </span>
                          <div className="ml-4 flex items-center gap-1">
                            <button
                              onClick={() => handleOverride(m.id, "home")}
                              className={cn(
                                "rounded px-2.5 py-0.5 text-xs font-medium transition-colors",
                                choice === "home"
                                  ? "bg-blue-600 text-white"
                                  : "border bg-white text-gray-600 hover:bg-blue-50"
                              )}
                            >
                              {t("simulate.homeWins")}
                            </button>
                            <button
                              onClick={() => handleOverride(m.id, "away")}
                              className={cn(
                                "rounded px-2.5 py-0.5 text-xs font-medium transition-colors",
                                choice === "away"
                                  ? "bg-blue-600 text-white"
                                  : "border bg-white text-gray-600 hover:bg-blue-50"
                              )}
                            >
                              {t("simulate.awayWins")}
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
          {overrideMap.size > 0 && !scenarioSim && !scenarioLoading && !scenarioError && (
            <div className="mt-4 flex justify-end">
              <Button size="sm" onClick={runScenario}>
                <Play size={13} className="mr-1" />
                {t("simulate.runScenario")}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Scenario results */}
      {(scenarioSim || scenarioError) && (
        <div className="mt-6">
          <h2 className="text-lg font-semibold text-gray-900" data-cy="scenario-results-heading">
            {t("simulate.scenarioVsBaseline")}
          </h2>
          {scenarioError ? (
            <p className="mt-2 text-sm text-red-500">{t("simulate.scenarioError")}</p>
          ) : (
            scenarioSim && (
              <div className="mt-3 rounded-lg border bg-white shadow-sm overflow-hidden overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-[#F3F4F6]">
                      <TableHead className="font-semibold text-gray-700 sticky left-0 bg-[#F3F4F6]">
                        {t("simulate.participant")}
                      </TableHead>
                      {POSITIONS.map((pos) => (
                        <TableHead
                          key={pos}
                          className="text-center font-semibold"
                          style={{ color: POSITION_COLORS[pos] }}
                        >
                          {t(`positions.${pos}`)}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sortedEntries.map(([id], i) => {
                      const color = PARTICIPANT_COLORS[id] ?? "#6B7280";
                      const name = participantNames[id] ?? id;
                      const scenProbs = scenarioSim.probabilities[id];
                      const baseProbs = sim.probabilities[id];
                      return (
                        <TableRow key={id} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                          <TableCell className="font-medium sticky left-0 bg-inherit">
                            <div className="flex items-center gap-2">
                              <span
                                className="inline-block h-3 w-3 rounded-full shrink-0"
                                style={{ backgroundColor: color }}
                              />
                              {name}
                            </div>
                          </TableCell>
                          {POSITIONS.map((pos) => {
                            const basePct = baseProbs?.[pos] ?? 0;
                            const scenPct = scenProbs?.[pos] ?? 0;
                            const delta = scenPct - basePct;
                            return (
                              <TableCell key={pos} className="text-center text-sm">
                                <div className="font-mono">{pct(scenPct)}</div>
                                {Math.abs(delta) >= 0.001 && (
                                  <div
                                    className={cn(
                                      "text-xs font-medium",
                                      delta > 0 ? "text-green-600" : "text-red-500"
                                    )}
                                  >
                                    {delta > 0 ? "+" : ""}
                                    {(delta * 100).toFixed(1)}pp
                                  </div>
                                )}
                              </TableCell>
                            );
                          })}
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}
