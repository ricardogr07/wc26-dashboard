"use client";

import { useEffect, useState } from "react";
import { getSimulation } from "@/lib/api";
import { PARTICIPANT_COLORS } from "@/lib/mock-data";
import type { SimulationRun } from "@/lib/types";
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
import { RefreshCw, Lock } from "lucide-react";

const POSITIONS = ["1st", "2nd", "3rd", "4th", "5th"] as const;

const POSITION_COLORS = {
  "1st": "#F59E0B",
  "2nd": "#9CA3AF",
  "3rd": "#D97706",
  "4th": "#3B82F6",
  "5th": "#6B7280",
} as const;

function pct(val: number) {
  return `${(val * 100).toFixed(1)}%`;
}

function formatRunAt(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

export default function SimulatePage() {
  const [simulation, setSimulation] = useState<SimulationRun | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getSimulation().then(setSimulation).catch(() => setError(true));
  }, []);

  if (!simulation && !error) {
    return <p className="mx-auto max-w-5xl px-4 py-16 text-sm text-gray-500">Loading simulation…</p>;
  }
  if (error) {
    return <p className="mx-auto max-w-5xl px-4 py-16 text-sm text-red-500">Failed to load simulation.</p>;
  }

  const sim = simulation!;
  const participantNames = Object.fromEntries(
    Object.keys(sim.probabilities).map((id) => [id, id.charAt(0).toUpperCase() + id.slice(1)])
  );
  const sortedEntries = Object.entries(sim.probabilities).sort(
    (a, b) => b[1]["1st"] - a[1]["1st"]
  );

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* Metadata bar */}
      <div className="flex items-center gap-2 rounded-lg bg-gray-100 px-4 py-2.5 text-sm text-gray-500">
        <RefreshCw size={14} className="shrink-0" />
        <span>
          Last run: <span className="font-medium text-gray-700">{formatRunAt(sim.runAt)}</span>
          <span className="mx-2">·</span>
          <span className="font-medium text-gray-700">{sim.nRuns.toLocaleString()}</span> simulations
          <span className="mx-2">·</span>
          <span className="font-medium text-gray-700">{sim.matchesCompletedAtRun}</span> matches completed
        </span>
      </div>

      <h1 className="mt-6 text-2xl font-bold text-gray-900">Simulation</h1>
      <p className="mt-1 text-sm text-gray-500">
        Monte Carlo win probability by final position for each participant.
      </p>

      {/* Probability chart */}
      <div className="mt-6 rounded-lg border bg-white shadow-sm p-4">
        <ProbabilityChart simulation={sim} participantNames={participantNames} />
      </div>

      {/* Probability table */}
      <div className="mt-6 rounded-lg border bg-white shadow-sm overflow-hidden overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-[#F3F4F6]">
              <TableHead className="font-semibold text-gray-700 sticky left-0 bg-[#F3F4F6]">
                PARTICIPANT
              </TableHead>
              {POSITIONS.map((pos) => (
                <TableHead key={pos} className="text-center font-semibold" style={{ color: POSITION_COLORS[pos] }}>
                  {pos}
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

      {/* Scenario Builder — locked */}
      <Card className="mt-6 opacity-50 pointer-events-none select-none">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Lock size={16} />
            Scenario Builder
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">
            Coming in a future update — select hypothetical winners and see how probabilities shift.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
