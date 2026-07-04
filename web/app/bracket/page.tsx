"use client";

import { useEffect, useState } from "react";
import { getMatches, type ApiMatch } from "@/lib/api";
import { BracketTree, type BracketMatchesByRound } from "@/components/bracket-tree";
import { PageSkeleton } from "@/components/page-skeleton";
import { useT } from "@/lib/locale-context";

type KnockoutRound = "r32" | "r16" | "qf" | "sf" | "final";
const KNOCKOUT_ROUNDS: KnockoutRound[] = ["r32", "r16", "qf", "sf", "final"];

// Explicit bracket slot order so that visual positions match actual connections:
// left[2N-1] and left[2N] both feed into the match at the next round's position N.
// R32 left: slots 1-8 feed R16 left; R32 right: slots 9-16 feed R16 right.
// QF order is [qf_97, qf_99, qf_98, qf_100] so each adjacent R16 pair feeds the correct QF.
const BRACKET_SLOT_ORDER: Partial<Record<KnockoutRound, string[]>> = {
  r32: [
    "r32_73","r32_75","r32_74","r32_77","r32_76","r32_78","r32_79","r32_80", // left → r16_90,89,91,92
    "r32_83","r32_84","r32_81","r32_82","r32_86","r32_88","r32_85","r32_87", // right → r16_93,94,95,96
  ],
  r16: [
    "r16_90","r16_89","r16_91","r16_92", // left → qf_97, qf_99
    "r16_93","r16_94","r16_95","r16_96", // right → qf_98, qf_100
  ],
  qf: ["qf_97","qf_99","qf_98","qf_100"],
  sf: ["sf_101","sf_102"],
};

function groupByRound(matches: ApiMatch[]): BracketMatchesByRound {
  const byRound: BracketMatchesByRound = { r32: [], r16: [], qf: [], sf: [], final: [] };
  for (const m of matches) {
    if (m.round !== "group") {
      byRound[m.round as KnockoutRound].push(m);
    }
  }
  for (const round of KNOCKOUT_ROUNDS) {
    const order = BRACKET_SLOT_ORDER[round];
    if (order) {
      const idx = new Map(order.map((id, i) => [id, i]));
      byRound[round].sort((a, b) => (idx.get(a.id) ?? 999) - (idx.get(b.id) ?? 999));
    } else {
      byRound[round].sort((a, b) => a.scheduledAt.localeCompare(b.scheduledAt));
    }
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
