"use client";

import { Badge } from "@/components/ui/badge";
import type { TeamStatus, MatchStatus } from "@/lib/types";
import { useT } from "@/lib/locale-context";

const STATUS_STYLES: Record<TeamStatus | MatchStatus, string> = {
  active:     "bg-green-100 text-green-800 border-green-200",
  eliminated: "bg-red-100 text-red-800 border-red-200",
  champion:   "bg-amber-100 text-amber-800 border-amber-200",
  qualified:  "bg-blue-100 text-blue-800 border-blue-200",
  scheduled:  "bg-gray-100 text-gray-600 border-gray-200",
  live:       "bg-green-100 text-green-800 border-green-300 animate-pulse",
  completed:  "bg-gray-100 text-gray-600 border-gray-200",
};

interface StatusBadgeProps {
  status: TeamStatus | MatchStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const t = useT();
  return (
    <Badge variant="outline" className={STATUS_STYLES[status]} data-cy="status-badge">
      {t(`status.${status}`)}
    </Badge>
  );
}
