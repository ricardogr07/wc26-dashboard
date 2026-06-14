"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from "recharts";
import { PARTICIPANT_COLORS } from "@/lib/constants";
import type { SimulationRun } from "@/lib/types";

interface WinnerProbabilityChartProps {
  simulation: SimulationRun;
  participantNames: Record<string, string>;
}

type ChartRow = { name: string; participantId: string; winPct: number };

type TooltipProps = {
  active?: boolean;
  payload?: { payload: ChartRow; value: number }[];
};

const CustomTooltip = ({ active, payload }: TooltipProps) => {
  if (!active || !payload?.length) return null;
  const { payload: row, value } = payload[0];
  const color = PARTICIPANT_COLORS[row.participantId] ?? "#6B7280";
  return (
    <div className="rounded-lg border bg-white p-3 shadow-lg text-sm">
      <p className="font-semibold" style={{ color }}>
        {row.name}
      </p>
      <p className="mt-1 text-gray-700">
        Win probability: <span className="font-mono font-semibold">{(value * 100).toFixed(1)}%</span>
      </p>
    </div>
  );
};

type YAxisTickProps = {
  x: string | number;
  y: string | number;
  payload: { value: string };
};

export function WinnerProbabilityChart({ simulation, participantNames }: WinnerProbabilityChartProps) {
  const data: ChartRow[] = Object.entries(simulation.winProbabilities)
    .sort(([, a], [, b]) => b - a)
    .map(([id, prob]) => ({
      name: participantNames[id] ?? id,
      participantId: id,
      winPct: prob,
    }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart
        layout="vertical"
        data={data}
        margin={{ top: 8, right: 48, left: 64, bottom: 8 }}
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
            const color = entry
              ? (PARTICIPANT_COLORS[entry.participantId] ?? "#6B7280")
              : "#6B7280";
            return (
              <text
                x={Number(props.x)}
                y={Number(props.y)}
                dy={4}
                textAnchor="end"
                fill={color}
                fontSize={13}
                fontWeight={600}
              >
                {props.payload.value}
              </text>
            );
          }}
          width={60}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="winPct" radius={[0, 4, 4, 0]}>
          {data.map((entry) => (
            <Cell
              key={entry.participantId}
              fill={PARTICIPANT_COLORS[entry.participantId] ?? "#6B7280"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
