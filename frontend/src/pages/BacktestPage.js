import React, { useState, useContext } from "react";
import { DashboardThemeContext } from "../theme";
import BacktestPanel from "../components/dashboard/BacktestPanel";
import TickerSearch from "../components/dashboard/TickerSearch";

const DEFAULT_TICKERS = ["SPY", "QQQ", "IWM", "GLD", "TLT"];

const OBJECTIVES = [
  { value: "markowitz", label: "Max Sharpe (Markowitz)" },
  { value: "min_variance", label: "Min Variance" },
  { value: "hrp", label: "HRP" },
  { value: "equal_weight", label: "Equal Weight" },
  { value: "qubo_sa", label: "QUBO-SA" },
  { value: "vqe", label: "VQE" },
  { value: "hybrid", label: "Hybrid Pipeline" },
];

export default function BacktestPage() {
  const colors = useContext(DashboardThemeContext);
  const [tickers, setTickers] = useState(DEFAULT_TICKERS);
  const [startDate, setStartDate] = useState("2022-01-01");
  const [endDate, setEndDate] = useState("2024-12-31");
  const [objective, setObjective] = useState("markowitz");

  const inputStyle = {
    background: colors.surfaceLight,
    border: `1px solid ${colors.border}`,
    borderRadius: 6,
    color: colors.text,
    padding: "6px 10px",
    fontSize: 13,
  };

  const labelStyle = { fontSize: 11, color: colors.textMuted, marginBottom: 4, display: "block" };

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1100 }}>
      <h1 style={{ color: colors.text, fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Backtest
      </h1>
      <p style={{ color: colors.textMuted, fontSize: 13, marginBottom: 28 }}>
        Run historical backtests across any date range and optimization method.
      </p>

      {/* Config row */}
      <div
        style={{
          display: "flex",
          gap: 20,
          flexWrap: "wrap",
          background: colors.surface,
          border: `1px solid ${colors.border}`,
          borderRadius: 10,
          padding: "20px 24px",
          marginBottom: 24,
        }}
      >
        <div style={{ flex: "1 1 220px" }}>
          <label style={labelStyle}>Tickers</label>
          <TickerSearch value={tickers} onChange={setTickers} />
        </div>

        <div>
          <label style={labelStyle}>Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            style={inputStyle}
          />
        </div>

        <div>
          <label style={labelStyle}>End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            style={inputStyle}
          />
        </div>

        <div>
          <label style={labelStyle}>Optimization Method</label>
          <select
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            style={{ ...inputStyle, cursor: "pointer" }}
          >
            {OBJECTIVES.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Backtest panel */}
      <BacktestPanel
        tickers={tickers}
        startDate={startDate}
        endDate={endDate}
        objective={objective}
        onBacktestComplete={() => {}}
      />
    </div>
  );
}
