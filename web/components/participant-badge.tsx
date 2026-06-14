import { PARTICIPANT_COLORS } from "@/lib/constants";

interface ParticipantBadgeProps {
  participantId: string;
  displayName: string;
  className?: string;
}

export function ParticipantBadge({ participantId, displayName, className }: ParticipantBadgeProps) {
  const color = PARTICIPANT_COLORS[participantId] ?? "#6B7280";
  return (
    <span className={`inline-flex items-center gap-1.5 ${className ?? ""}`}>
      <span
        className="inline-block h-3 w-3 rounded-full flex-shrink-0"
        style={{ backgroundColor: color }}
      />
      <span className="font-medium">{displayName}</span>
    </span>
  );
}
