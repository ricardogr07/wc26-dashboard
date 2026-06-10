import { StatusBadge } from "./status-badge";
import type { Team } from "@/lib/types";

const STATUS_PILL_STYLES: Record<string, string> = {
  active:     "bg-green-50 text-green-800 border border-green-200",
  eliminated: "bg-red-50 text-red-700 border border-red-200 opacity-70",
  champion:   "bg-amber-50 text-amber-800 border border-amber-200",
  qualified:  "bg-blue-50 text-blue-800 border border-blue-200",
};

interface TeamPillProps {
  team: Team;
  showStatus?: boolean;
}

export function TeamPill({ team, showStatus = true }: TeamPillProps) {
  const pillStyle = STATUS_PILL_STYLES[team.status] ?? "bg-gray-50 text-gray-700 border border-gray-200";
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${pillStyle}`}>
      <span className="font-mono text-[10px] font-bold">{team.id}</span>
      {showStatus && <StatusBadge status={team.status} />}
    </span>
  );
}

interface TeamRowProps {
  team: Team;
}

export function TeamRow({ team }: TeamRowProps) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <div className="flex items-center gap-2">
        <div className="h-4 w-6 rounded bg-gray-200 text-[9px] flex items-center justify-center font-bold text-gray-500">
          {team.id.slice(0, 3)}
        </div>
        <span className="text-sm">{team.name}</span>
      </div>
      <StatusBadge status={team.status} />
    </div>
  );
}
