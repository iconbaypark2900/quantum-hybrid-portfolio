import React, { useState, useContext } from "react";
import { DashboardThemeContext } from "../theme";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import { optimizePortfolio } from "../services/api";
import { generateMarketData, runEnhancedQSWOptimization } from "../lib/simulationEngine";
import TickerSearch from "../components/dashboard/TickerSearch";
import SectionTitle from "../components/dashboard/SectionTitle";
import WhatIfAdjuster from "../components/dashboard/WhatIfAdjuster";

const DEFAULT_TICKERS = ["SPY", "QQQ", "IWM", "GLD", "TLT"];

const STRESS_SCENARIOS = [
  { name: "2008 Crisis", shock: -0.40, color: "#EF4444" },
  { name: "COVID Crash", shock: -0.34, color: "#F59E0B" },
  { name: "Rate Hike +300bps", shock: -0.18, color: "#8B5CF6" },
  { name: "Tech Selloff", shock: -0.25, color: "#EC4899" },
  { name: "Bull Market", shock: +0.28, color: "#10B981" },
];

function MetricBox({ label, value, color, colors }) {
  return (
    <div
      style={{
        background: colors.surfaceLight,
        border: `1px solid ${colors.border}`,
        borderRadius: 8,
        padding: "14px 18px",
        flex: "1 1 160px",
      }}
    >
      <div style={{ fontSize: 11, color: colors.textMuted, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: color || colors.text }}>{value}</div>
    </div>
  );
}

export default function RiskPage() {
  const colors = useContext(DashboardThemeContext);
  const [tickers, setTickers] = useState(DEFAULT_TICKERS);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await optimizePortfolio({ tickers, objective: "markowitz", use_simulation: true });
      setResult(res);
    } catch {
      try {
        const data = generateMarketData(tickers.length, 252, "normal", 42, tickers);
        const sim = runEnhancedQSWOptimization(data, 0.3, 10, 0.1, 0.2);
        setResult(sim);
      } catch (e) {
        setError(e.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const varVal = result?.var_95 != null
    ? `${(result.var_95 * 100).toFixed(2)}%`
    : result?.volatility != null
    ? `${(result.volatility * 0.165 * 100).toFixed(2)}%`
    : "—";

  const vol = result?.volatility != null
    ? `${(result.volatility * 100).toFixed(2)}%`
    : "—";

  const sharpe = result?.sharpe_ratio != null
    ? result.sharpe_ratio.toFixed(3)
    : "—";

  const maxDD = result?.max_drawdown != null
    ? `${(result.max_drawdown * 100).toFixed(2)}%`
    : "—";

  const holdings = result?.holdings || result?.weights
    ? Object.entries(result.weights || {}).map(([name, weight]) => ({ name, weight }))
    : [];

  const stressData = STRESS_SCENARIOS.map((s) => ({
    name: s.name,
    impact: +(s.shock * 100).toFixed(1),
    fill: s.color,
  }));

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1100 }}>
      <h1 style={{ color: colors.text, fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Risk Analysis
      </h1>
      <p style={{ color: colors.textMuted, fontSize: 13, marginBottom: 24 }}>
        VaR, stress tests, drawdown, and what-if weight adjustments.
      </p>

      {/* Controls */}
      <div
        style={{
          display: "flex",
          gap: 16,
          alignItems: "flex-end",
          flexWrap: "wrap",
          background: colors.surface,
          border: `1px solid ${colors.border}`,
          borderRadius: 10,
          padding: "18px 24px",
          marginBottom: 24,
        }}
      >
        <div style={{ flex: "1 1 260px" }}>
          <div style={{ fontSize: 11, color: colors.textMuted, marginBottom: 4 }}>Tickers</div>
          <TickerSearch value={tickers} onChange={setTickers} />
        </div>
        <button
          onClick={runAnalysis}
          disabled={loading}
          style={{
            padding: "8px 22px",
            background: loading ? colors.border : "#3B82F6",
            color: "#fff",
            border: "none",
            borderRadius: 7,
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: 600,
            fontSize: 13,
          }}
        >
          {loading ? "Running…" : "Run Analysis"}
        </button>
      </div>

      {error && (
        <div style={{ color: colors.red, marginBottom: 16, fontSize: 13 }}>{error}</div>
      )}

      {/* Metrics */}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 24 }}>
        <MetricBox label="Daily VaR (95%)" value={varVal} color={colors.red} colors={colors} />
        <MetricBox label="Annualized Vol" value={vol} color={colors.orange} colors={colors} />
        <MetricBox label="Sharpe Ratio" value={sharpe} color={colors.green} colors={colors} />
        <MetricBox label="Max Drawdown" value={maxDD} color={colors.red} colors={colors} />
      </div>

      {/* Stress Test Chart */}
      <div
        style={{
          background: colors.surface,
          border: `1px solid ${colors.border}`,
          borderRadius: 10,
          padding: "20px 24px",
          marginBottom: 24,
        }}
      >
        <SectionTitle title="Stress Test Scenarios" colors={colors} />
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={stressData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
            <XAxis dataKey="name" tick={{ fill: colors.textMuted, fontSize: 11 }} />
            <YAxis tickFormatter={(v) => `${v}%`} tick={{ fill: colors.textMuted, fontSize: 11 }} />
            <Tooltip
              formatter={(v) => [`${v}%`, "Portfolio Impact"]}
              contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 6 }}
              labelStyle={{ color: colors.text }}
            />
            <ReferenceLine y={0} stroke={colors.border} />
            <Bar dataKey="impact" radius={[4, 4, 0, 0]}>
              {stressData.map((entry, i) => (
                <rect key={i} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* What-if adjuster */}
      {holdings.length > 0 && (
        <div
          style={{
            background: colors.surface,
            border: `1px solid ${colors.border}`,
            borderRadius: 10,
            padding: "20px 24px",
          }}
        >
          <WhatIfAdjuster holdings={holdings} onWeightsChanged={() => {}} />
        </div>
      )}
    </div>
  );
}
