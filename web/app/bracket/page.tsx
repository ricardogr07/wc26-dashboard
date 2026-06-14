"use client";

import { useEffect, useState } from "react";
import { getMatches, type ApiMatch } from "@/lib/api";
import { BracketTree, type BracketMatchesByRound } from "@/components/bracket-tree";
import { PageSkeleton } from "@/components/page-skeleton";
import { useT } from "@/lib/locale-context";

type KnockoutRound = "r32" | "r16" | "qf" | "sf" | "final";
const KNOCKOUT_ROUNDS: KnockoutRound[] = ["r32", "r16", "qf", "sf", "final"];

function groupByRound(matches: ApiMatch[]): BracketMatchesByRound {
  const byRound: BracketMatchesByRound = { r32: [], r16: [], qf: [], sf: [], final: [] };
  for (const m of matches) {
    if (m.round !== "group") {
      byRound[m.round as KnockoutRound].push(m);
    }
  }
  // Sort each round by scheduledAt so bracket order is preserved
  for (const round of KNOCKOUT_ROUNDS) {
    byRound[round].sort((a, b) => a.scheduledAt.localeCompare(b.scheduledAt));
  }
  return byRound;
}

export default function BracketPage() {
  const [matches, setMatches] = useState<ApiMatch[] | null>(null);
  const [error, setError] = useState(false);
  const t = useT();

  useEffect(() => {
    getMatches()
      .then((all) => setMatches(all.filter((m) => m.round !== "group")))
      .catch(() => setError(true));
  }, []);

  if (!matches && !error) return <PageSkeleton />;
  if (error) {
    return (
      <p className="mx-auto max-w-5xl px-4 py-16 text-sm text-red-500">{t("bracket.error")}</p>
    );
  }

  const matchesByRound = groupByRound(matches!);

  return (
    <div className="mx-auto max-w-screen-2xl px-4 py-8">
      <h1 data-cy="bracket-heading" className="text-2xl font-bold text-gray-900">{t("bracket.title")}</h1>
      <p className="mt-1 text-sm text-gray-500">{t("bracket.subtitle")}</p>
      <div className="mt-6 overflow-x-auto rounded-lg border bg-gray-50 p-4">
        <BracketTree matchesByRound={matchesByRound} />
      </div>
    </div>
  );
}
