import { Badge } from "@/components/ui/badge";
import type { TeamStatus, MatchStatus } from "@/lib/types";

const STATUS_STYLES: Record<TeamStatus | MatchStatus, string> = {
  active:     "bg-green-100 text-green-800 border-green-200",
  eliminated: "bg-red-100 text-red-800 border-red-200",
  champion:   "bg-amber-100 text-amber-800 border-amber-200",
  qualified:  "bg-blue-100 text-blue-800 border-blue-200",
  scheduled:  "bg-gray-100 text-gray-600 border-gray-200",
  live:       "bg-green-100 text-green-800 border-green-300 animate-pulse",
  completed:  "bg-gray-100 text-gray-600 border-gray-200",
};

const STATUS_LABELS: Record<TeamStatus | MatchStatus, string> = {
  active:     "Active",
  eliminated: "Eliminated",
  champion:   "Champion",
  qualified:  "Qualified",
  scheduled:  "Scheduled",
  live:       "Live",
  completed:  "FT",
};

interface StatusBadgeProps {
  status: TeamStatus | MatchStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <Badge variant="outline" className={STATUS_STYLES[status]}>
      {STATUS_LABELS[status]}
    </Badge>
  );
}
