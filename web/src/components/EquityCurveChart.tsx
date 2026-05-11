"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useThemePreference } from "@/context/ThemeContext";

interface EquityCurveChartProps {
  dates: string[];
  portfolioValues: number[];
  benchmarkValues?: number[];
  title?: string;
}

export default function EquityCurveChart({
  dates,
  portfolioValues,
  benchmarkValues,
  title,
}: EquityCurveChartProps) {
  const { resolved } = useThemePreference();
  const gridStroke =
    resolved === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.08)";
  const portfolioColor = "var(--color-ql-primary, #22c55e)";
  const benchmarkColor = "var(--color-ql-outline, #94a3b8)";

  if (dates.length === 0) {
    return (
      <p className="text-xs text-ql-muted py-6 text-center">
        No equity curve data available.
      </p>
    );
  }

  const labelInterval = Math.max(1, Math.floor(dates.length / 8));

  const data = dates.map((d, i) => ({
    date: d,
    portfolio: portfolioValues[i] ?? 1,
    ...(benchmarkValues ? { benchmark: benchmarkValues[i] ?? 1 } : {}),
  }));

  return (
    <div>
      {title && (
        <h4 className="text-[10px] uppercase tracking-widest text-ql-muted font-bold mb-2">
          {title}
        </h4>
      )}
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 8 }}>
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
            tickFormatter={(v: number) => v.toFixed(2)}
            domain={["auto", "auto"]}
          />
          <Tooltip
            contentStyle={{ fontSize: 11 }}
            formatter={(v, name) => [
              typeof v === "number" ? v.toFixed(4) : String(v),
              name === "portfolio" ? "Portfolio" : "Benchmark",
            ]}
            labelFormatter={(label) => `Date: ${String(label)}`}
          />
          <Legend wrapperStyle={{ fontSize: 10 }} />
          <Line
            type="monotone"
            dataKey="portfolio"
            stroke={portfolioColor}
            strokeWidth={2}
            dot={false}
            name="Portfolio"
          />
          {benchmarkValues && (
            <Line
              type="monotone"
              dataKey="benchmark"
              stroke={benchmarkColor}
              strokeWidth={1.5}
              strokeDasharray="4 2"
              dot={false}
              name="Benchmark"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
