"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { PARTICIPANT_COLORS } from "@/lib/mock-data";
import type { SimulationRun } from "@/lib/types";

const POSITION_COLORS = {
  "1st": "#F59E0B",
  "2nd": "#9CA3AF",
  "3rd": "#D97706",
  "4th": "#3B82F6",
  "5th": "#6B7280",
} as const;

interface ProbabilityChartProps {
  simulation: SimulationRun;
  participantNames: Record<string, string>;
}

type ChartRow = {
  name: string;
  participantId: string;
  "1st": number;
  "2nd": number;
  "3rd": number;
  "4th": number;
  "5th": number;
};

function pct(val: number) {
  return `${(val * 100).toFixed(1)}%`;
}

type TooltipProps = {
  active?: boolean;
  payload?: { name: string; value: number }[];
  label?: string;
};

const CustomTooltip = ({ active, payload, label }: TooltipProps) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-white p-3 shadow-lg text-sm">
      <p className="font-semibold mb-1">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: POSITION_COLORS[entry.name as keyof typeof POSITION_COLORS] }}>
          {entry.name}: {pct(entry.value)}
        </p>
      ))}
    </div>
  );
};

type YAxisTickProps = {
  x: string | number;
  y: string | number;
  payload: { value: string };
};

export function ProbabilityChart({ simulation, participantNames }: ProbabilityChartProps) {
  const data: ChartRow[] = Object.entries(simulation.probabilities)
    .sort((a, b) => b[1]["1st"] - a[1]["1st"])
    .map(([id, probs]) => ({
      name: participantNames[id] ?? id,
      participantId: id,
      "1st": probs["1st"],
      "2nd": probs["2nd"],
      "3rd": probs["3rd"],
      "4th": probs["4th"],
      "5th": probs["5th"],
    }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart
        layout="vertical"
        data={data}
        margin={{ top: 8, right: 24, left: 64, bottom: 8 }}
      >
        <XAxis
          type="number"
          domain={[0, 1]}
          tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
          tick={{ fontSize: 12 }}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={(props: YAxisTickProps) => {
            const entry = data.find((d) => d.name === props.payload.value);
            const color = entry ? (PARTICIPANT_COLORS[entry.participantId] ?? "#6B7280") : "#6B7280";
            return (
              <text x={Number(props.x)} y={Number(props.y)} dy={4} textAnchor="end" fill={color} fontSize={13} fontWeight={600}>
                {props.payload.value}
              </text>
            );
          }}
          width={60}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          formatter={(value: string) => (
            <span style={{ color: POSITION_COLORS[value as keyof typeof POSITION_COLORS] }}>{value}</span>
          )}
        />
        {(["1st", "2nd", "3rd", "4th", "5th"] as const).map((pos) => (
          <Bar
            key={pos}
            dataKey={pos}
            stackId="a"
            fill={POSITION_COLORS[pos]}
            radius={pos === "5th" ? [0, 4, 4, 0] : undefined}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
