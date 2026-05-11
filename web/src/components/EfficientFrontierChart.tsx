"use client";

import {
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useThemePreference } from "@/context/ThemeContext";

export interface EfficientFrontierPoint {
  objective: string;
  volatility: number;
  expected_return: number;
  sharpe: number;
}

interface EfficientFrontierChartProps {
  points: EfficientFrontierPoint[];
}

const PALETTE = [
  "var(--color-ql-primary, #22c55e)",
  "var(--color-ql-secondary, #3b82f6)",
  "var(--color-ql-tertiary, #a855f7)",
  "#f59e0b",
  "#ef4444",
  "#06b6d4",
  "#84cc16",
  "#f97316",
];

interface FrontierTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: EfficientFrontierPoint }>;
}

function FrontierTooltip({ active, payload }: FrontierTooltipProps) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg border border-ql-border bg-ql-surface p-2 text-xs shadow-md">
      <p className="font-bold mb-1">{d.objective}</p>
      <p>Return: {d.expected_return.toFixed(1)}%</p>
      <p>Volatility: {d.volatility.toFixed(1)}%</p>
      <p>Sharpe: {d.sharpe.toFixed(3)}</p>
    </div>
  );
}

export default function EfficientFrontierChart({
  points,
}: EfficientFrontierChartProps) {
  const { resolved } = useThemePreference();
  const gridStroke =
    resolved === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.08)";

  if (points.length === 0) {
    return (
      <p className="text-xs text-ql-muted py-6 text-center">
        Run a simulation comparison to see the frontier.
      </p>
    );
  }

  const sorted = [...points].sort((a, b) => b.sharpe - a.sharpe);

  const data = sorted.map((p) => ({
    ...p,
    x: p.volatility,
    y: p.expected_return,
    label: p.objective,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ScatterChart margin={{ top: 20, right: 24, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
        <XAxis
          type="number"
          dataKey="x"
          name="Volatility"
          tick={{ fontSize: 10, fill: "currentColor" }}
          tickFormatter={(v: number) => `${v.toFixed(0)}%`}
          label={{
            value: "Volatility (%)",
            position: "insideBottom",
            offset: -2,
            fontSize: 10,
            fill: "currentColor",
          }}
        />
        <YAxis
          type="number"
          dataKey="y"
          name="Return"
          tick={{ fontSize: 10, fill: "currentColor" }}
          tickFormatter={(v: number) => `${v.toFixed(0)}%`}
          label={{
            value: "Return (%)",
            angle: -90,
            position: "insideLeft",
            fontSize: 10,
            fill: "currentColor",
          }}
        />
        <Tooltip content={<FrontierTooltip />} />
        <Scatter data={data}>
          {data.map((_d, i) => (
            <Cell
              key={i}
              fill={PALETTE[i % PALETTE.length]}
              r={7}
            />
          ))}
          <LabelList
            dataKey="label"
            position="top"
            offset={10}
            style={{ fontSize: 9, fill: "currentColor" }}
          />
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  );
}
