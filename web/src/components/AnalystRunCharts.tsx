"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/**
 * During browser print, ResponsiveContainer measures its parent as 0px wide
 * because the layout reflows before Recharts can measure. Bumping this key on
 * beforeprint forces a React re-render after the print layout is applied, so
 * Recharts picks up the stable width set by the @media print CSS rule.
 */
function usePrintLayout(): number {
  const [printKey, setPrintKey] = useState(0);
  useEffect(() => {
    const onBefore = () => setPrintKey((k) => k + 1);
    const onAfter = () => setPrintKey((k) => k + 1);
    window.addEventListener("beforeprint", onBefore);
    window.addEventListener("afterprint", onAfter);
    return () => {
      window.removeEventListener("beforeprint", onBefore);
      window.removeEventListener("afterprint", onAfter);
    };
  }, []);
  return printKey;
}

const MAX_HOLDINGS = 12;

const SECTOR_COLORS = [
  "var(--color-ql-primary, #22c55e)",
  "var(--color-ql-secondary, #3b82f6)",
  "var(--color-ql-tertiary, #a855f7)",
  "#f59e0b",
  "#ef4444",
  "#06b6d4",
  "#84cc16",
  "#f97316",
  "#8b5cf6",
  "#14b8a6",
];

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[10px] uppercase tracking-widest text-ql-muted font-bold mb-3">
      {children}
    </h3>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <p className="text-xs text-ql-muted py-6 text-center">{label}</p>
  );
}

type HoldingRow = { name?: unknown; weight?: unknown; sector?: unknown };

function parseHoldings(merged: Record<string, unknown>): { name: string; weight: number }[] {
  const raw = merged.holdings;
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((h): h is HoldingRow => h != null && typeof h === "object")
    .map((h) => ({
      name: String(h.name ?? ""),
      weight: typeof h.weight === "number" ? h.weight : Number(h.weight),
    }))
    .filter((h) => Number.isFinite(h.weight) && h.weight > 1e-6)
    .sort((a, b) => b.weight - a.weight)
    .slice(0, MAX_HOLDINGS);
}

type SectorRow = { sector?: unknown; weight?: unknown };

function parseSectors(merged: Record<string, unknown>): { name: string; value: number }[] {
  const raw = merged.sector_allocation;
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((s): s is SectorRow => s != null && typeof s === "object")
    .map((s) => ({
      name: String(s.sector ?? ""),
      value: typeof s.weight === "number" ? s.weight : Number(s.weight),
    }))
    .filter((s) => Number.isFinite(s.value) && s.value > 1e-6)
    .sort((a, b) => b.value - a.value);
}

type BenchmarkEntry = { name: string; sharpe: number; expected_return: number; volatility: number };

function parseBenchmarks(merged: Record<string, unknown>): BenchmarkEntry[] {
  const raw = merged.benchmarks as Record<string, unknown> | undefined;
  if (!raw || typeof raw !== "object") return [];

  const portfolio: BenchmarkEntry = {
    name: "Portfolio",
    sharpe: typeof merged.sharpe_ratio === "number" ? merged.sharpe_ratio : 0,
    expected_return: typeof merged.expected_return === "number" ? merged.expected_return : 0,
    volatility: typeof merged.volatility === "number" ? merged.volatility : 0,
  };

  const benches: BenchmarkEntry[] = Object.entries(raw).map(([k, v]) => {
    const rec = v as Record<string, unknown>;
    return {
      name: k.replace(/_/g, " "),
      sharpe: typeof rec.sharpe === "number" ? rec.sharpe : 0,
      expected_return: typeof rec.expected_return === "number" ? rec.expected_return : 0,
      volatility: typeof rec.volatility === "number" ? rec.volatility : 0,
    };
  });

  return [portfolio, ...benches];
}

function pct(v: number) {
  return `${(v * 100).toFixed(2)}%`;
}

/** Single chart props: all data comes from `merged` — the one merged optimize response. */
export default function AnalystRunCharts({
  merged,
}: {
  merged: Record<string, unknown>;
}) {
  const holdings = parseHoldings(merged);
  const sectors = parseSectors(merged);
  const benchmarks = parseBenchmarks(merged);
  const printKey = usePrintLayout();

  return (
    <div className="space-y-8">
      {/* Holdings bar chart */}
      <div className="print-chart-card">
        <SectionHeader>Portfolio Holdings</SectionHeader>
        {holdings.length === 0 ? (
          <EmptyState label="No holdings data" />
        ) : (
          <ResponsiveContainer key={`holdings-${printKey}`} width="100%" height={240}>
            <BarChart
              data={holdings.map((h) => ({
                name: h.name,
                weight: parseFloat((h.weight * 100).toFixed(2)),
              }))}
              margin={{ top: 4, right: 16, left: 0, bottom: 32 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 10, fill: "currentColor" }}
                angle={-35}
                textAnchor="end"
                interval={0}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "currentColor" }}
                tickFormatter={(v: number) => `${v}%`}
              />
              <Tooltip
                formatter={(v) => [`${String(v)}%`, "Weight"]}
                contentStyle={{ fontSize: 11 }}
              />
              <Bar dataKey="weight" radius={[3, 3, 0, 0]} maxBarSize={36}>
                {holdings.map((_h, i) => (
                  <Cell
                    key={i}
                    fill={SECTOR_COLORS[i % SECTOR_COLORS.length]}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Sector allocation pie */}
      {sectors.length > 0 && (
        <div className="print-chart-card">
          <SectionHeader>Sector Allocation</SectionHeader>
          <ResponsiveContainer key={`sectors-${printKey}`} width="100%" height={220}>
            <PieChart>
              <Pie
                data={sectors}
                dataKey="value"
                nameKey="name"
                outerRadius={80}
                label={({ name, value }) =>
                  `${String(name ?? "")} ${typeof value === "number" ? pct(value) : ""}`
                }
                labelLine={false}
              >
                {sectors.map((_s, i) => (
                  <Cell
                    key={i}
                    fill={SECTOR_COLORS[i % SECTOR_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip
                formatter={(v) => [typeof v === "number" ? pct(v) : String(v), "Weight"]}
                contentStyle={{ fontSize: 11 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Benchmark comparison */}
      {benchmarks.length > 1 && (
        <div className="print-chart-card">
          <SectionHeader>Benchmark comparison</SectionHeader>
          <ResponsiveContainer key={`bench-${printKey}`} width="100%" height={220}>
            <BarChart
              data={benchmarks.map((b) => ({
                name: b.name,
                Sharpe: parseFloat(b.sharpe.toFixed(3)),
                Return: parseFloat((b.expected_return * 100).toFixed(2)),
                Vol: parseFloat((b.volatility * 100).toFixed(2)),
              }))}
              margin={{ top: 4, right: 16, left: 0, bottom: 32 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 10, fill: "currentColor" }}
                angle={-20}
                textAnchor="end"
                interval={0}
              />
              <YAxis tick={{ fontSize: 10, fill: "currentColor" }} />
              <Tooltip contentStyle={{ fontSize: 11 }} />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              <Bar dataKey="Sharpe" fill={SECTOR_COLORS[0]} maxBarSize={24} />
              <Bar dataKey="Return" fill={SECTOR_COLORS[1]} maxBarSize={24} />
              <Bar dataKey="Vol" fill={SECTOR_COLORS[4]} maxBarSize={24} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
