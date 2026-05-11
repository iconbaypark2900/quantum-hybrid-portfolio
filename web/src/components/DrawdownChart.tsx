"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useThemePreference } from "@/context/ThemeContext";

interface DrawdownChartProps {
  dates: string[];
  drawdowns: number[];
  maxDrawdown?: number;
}

export function deriveDrawdowns(cumulativeValues: number[]): number[] {
  let peak = cumulativeValues[0] ?? 1;
  return cumulativeValues.map((v) => {
    if (v > peak) peak = v;
    return peak > 0 ? (v - peak) / peak : 0;
  });
}

export default function DrawdownChart({
  dates,
  drawdowns,
  maxDrawdown,
}: DrawdownChartProps) {
  const { resolved } = useThemePreference();
  const gridStroke =
    resolved === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.08)";
  const errorColor = "var(--color-ql-error, #ef4444)";

  if (dates.length === 0) {
    return (
      <p className="text-xs text-ql-muted py-6 text-center">
        No drawdown data available.
      </p>
    );
  }

  const labelInterval = Math.max(1, Math.floor(dates.length / 8));

  const data = dates.map((d, i) => ({
    date: d,
    drawdown: drawdowns[i] ?? 0,
  }));

  return (
    <div>
      <h4 className="text-[10px] uppercase tracking-widest text-ql-muted font-bold mb-2">
        Drawdown
      </h4>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 9, fill: "currentColor" }}
            interval={labelInterval}
            angle={-20}
            textAnchor="end"
          />
          <YAxis
            tick={{ fontSize: 10, fill: "currentColor" }}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            domain={["auto", 0]}
          />
          <Tooltip
            contentStyle={{ fontSize: 11 }}
            formatter={(v) => [`${(Number(v) * 100).toFixed(2)}%`, "Drawdown"]}
            labelFormatter={(label) => `Date: ${String(label)}`}
          />
          <ReferenceLine y={0} stroke={gridStroke} />
          {maxDrawdown != null && maxDrawdown < 0 && (
            <ReferenceLine
              y={maxDrawdown}
              stroke={errorColor}
              strokeDasharray="4 2"
              label={{
                value: `Max ${(maxDrawdown * 100).toFixed(1)}%`,
                position: "insideTopLeft",
                fill: errorColor,
                fontSize: 10,
              }}
            />
          )}
          <Area
            type="monotone"
            dataKey="drawdown"
            stroke={errorColor}
            fill={errorColor}
            fillOpacity={0.2}
            strokeWidth={1.5}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
