import React, { useState, useContext } from "react";
import { DashboardThemeContext } from "../theme";
import RegimeComparison from "../components/dashboard/RegimeComparison";
import TickerSearch from "../components/dashboard/TickerSearch";
import scenarioPresets from "../data/scenarioPresets";

const DEFAULT_TICKERS = ["SPY", "QQQ", "IWM", "GLD", "TLT"];

const OBJECTIVES = [
  { value: "markowitz", label: "Max Sharpe" },
  { value: "min_variance", label: "Min Variance" },
  { value: "hrp", label: "HRP" },
  { value: "hybrid", label: "Hybrid" },
];

export default function ScenariosPage() {
  const colors = useContext(DashboardThemeContext);
  const [tickers, setTickers] = useState(DEFAULT_TICKERS);
  const [objective, setObjective] = useState("markowitz");
  const [activePreset, setActivePreset] = useState(null);

  const inputStyle = {
    background: colors.surfaceLight,
    border: `1px solid ${colors.border}`,
    borderRadius: 6,
    color: colors.text,
    padding: "6px 10px",
    fontSize: 13,
  };

  const applyPreset = (preset) => {
    setActivePreset(preset.name);
    if (preset.tickers) setTickers(preset.tickers);
    if (preset.objective) setObjective(preset.objective);
  };

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1100 }}>
      <h1 style={{ color: colors.text, fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Scenarios
      </h1>
      <p style={{ color: colors.textMuted, fontSize: 13, marginBottom: 24 }}>
        Compare performance across market regimes and run scenario presets.
      </p>

      {/* Config */}
      <div
        style={{
          background: colors.surface,
          border: `1px solid ${colors.border}`,
          borderRadius: 10,
          padding: "18px 24px",
          marginBottom: 20,
          display: "flex",
          gap: 20,
          flexWrap: "wrap",
          alignItems: "flex-end",
        }}
      >
        <div style={{ flex: "1 1 240px" }}>
          <div style={{ fontSize: 11, color: colors.textMuted, marginBottom: 4 }}>Tickers</div>
          <TickerSearch value={tickers} onChange={setTickers} />
        </div>

        <div>
          <div style={{ fontSize: 11, color: colors.textMuted, marginBottom: 4 }}>Method</div>
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

      {/* Preset Scenarios */}
      {scenarioPresets && scenarioPresets.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 12, color: colors.textMuted, marginBottom: 10, fontWeight: 600, letterSpacing: "0.05em" }}>
            QUICK PRESETS
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {scenarioPresets.slice(0, 8).map((preset) => (
              <button
                key={preset.name}
                onClick={() => applyPreset(preset)}
                style={{
                  padding: "6px 14px",
                  fontSize: 12,
                  fontWeight: 500,
                  background: activePreset === preset.name ? "rgba(59,130,246,0.2)" : colors.surfaceLight,
                  color: activePreset === preset.name ? "#3B82F6" : colors.textMuted,
                  border: `1px solid ${activePreset === preset.name ? "#3B82F6" : colors.border}`,
                  borderRadius: 20,
                  cursor: "pointer",
                  transition: "all 0.15s",
                }}
              >
                {preset.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Regime comparison */}
      <div
        style={{
          background: colors.surface,
          border: `1px solid ${colors.border}`,
          borderRadius: 10,
          padding: "20px 24px",
        }}
      >
        <RegimeComparison
          tickers={tickers}
          startDate="2020-01-01"
          endDate="2024-12-31"
          objective={objective}
          apiResult={null}
        />
      </div>
    </div>
  );
}
