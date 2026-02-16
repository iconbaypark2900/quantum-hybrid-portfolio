import React, { useState, useContext, useCallback, useRef } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from "recharts";
import { runBacktestBatch } from "../../services/api";
import { DashboardThemeContext, chartColors } from "../../theme";
import SectionTitle from "./SectionTitle";
import CustomTooltip from "./CustomTooltip";
import SCENARIO_PRESETS from "../../data/scenarioPresets";
import TickerSearch from "./TickerSearch";

let _uid = Date.now();
const uid = () => String(++_uid);

const EMPTY_SCENARIO = () => ({
  id: uid(),
  name: "",
  tickers: [],
  startDate: "2020-01-01",
  endDate: "2024-12-31",
});

function normalizeResult(raw) {
  if (!raw) return raw;
  const sm = raw.summary_metrics || {};
  const curve = (raw.results || raw.equity_curve || []).map((pt) => ({
    date: pt.date,
    value: pt.portfolio_value ?? pt.cumulative_value ?? 0,
  }));
  return {
    totalReturn: sm.total_return ?? raw.total_return ?? 0,
    annualReturn: sm.annual_return ?? raw.annual_return ?? 0,
    sharpe: sm.sharpe_ratio ?? raw.sharpe_ratio ?? 0,
    maxDrawdown: sm.max_drawdown ?? raw.max_drawdown ?? 0,
    volatility: sm.volatility ?? raw.volatility ?? 0,
    equityCurve: curve,
  };
}

function ScenarioTester({ objective, constraints, strategyPreset, omega, evolutionTime, regime, onLoadScenario }) {
  const colors = useContext(DashboardThemeContext);
  const [scenarios, setScenarios] = useState(() =>
    SCENARIO_PRESETS.map((p) => ({ ...p, id: uid() }))
  );
  const [results, setResults] = useState({});
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState("");
  const [showEquity, setShowEquity] = useState(false);
  const abortRef = useRef(false);

  const updateScenario = useCallback((id, field, value) => {
    setScenarios((prev) =>
      prev.map((s) => (s.id === id ? { ...s, [field]: value } : s))
    );
  }, []);

  const removeScenario = useCallback((id) => {
    setScenarios((prev) => prev.filter((s) => s.id !== id));
    setResults((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }, []);

  const addScenario = useCallback(() => {
    setScenarios((prev) => [...prev, EMPTY_SCENARIO()]);
  }, []);

  const loadPresets = useCallback(() => {
    const presets = SCENARIO_PRESETS.map((p) => ({ ...p, id: uid() }));
    setScenarios(presets);
    setResults({});
  }, []);

  const runAll = useCallback(async () => {
    const valid = scenarios.filter((s) => s.tickers.length > 0 && s.startDate && s.endDate);
    if (valid.length === 0) return;

    setRunning(true);
    abortRef.current = false;
    setProgress(`Running ${valid.length} scenario(s)...`);
    setResults({});

    const requests = valid.map((s) => ({
      tickers: s.tickers,
      start_date: s.startDate,
      end_date: s.endDate,
      rebalance_frequency: "monthly",
      objective: objective || "max_sharpe",
      strategy_preset: strategyPreset || "balanced",
      constraints: constraints || {},
      ...(omega != null && { omega }),
      ...(evolutionTime != null && { evolutionTime }),
      ...(regime && { regime }),
    }));

    try {
      const resp = await runBacktestBatch(requests);
      const newResults = {};
      (resp.results || []).forEach((item) => {
        const scenario = valid[item.index];
        if (!scenario) return;
        if (item.status === "ok") {
          newResults[scenario.id] = { ok: true, data: normalizeResult(item.result) };
        } else {
          newResults[scenario.id] = { ok: false, error: item.error || "Unknown error" };
        }
      });
      setResults(newResults);
      setProgress(`Completed ${resp.count || 0} of ${valid.length} scenario(s)`);
    } catch (err) {
      setProgress(`Batch failed: ${err.message}`);
    } finally {
      setRunning(false);
    }
  }, [scenarios, objective, strategyPreset, constraints]);

  const hasResults = Object.keys(results).length > 0;

  const equityData = useCallback(() => {
    const scenariosWithCurves = scenarios.filter(
      (s) => results[s.id]?.ok && results[s.id].data.equityCurve?.length > 0
    );
    if (scenariosWithCurves.length === 0) return [];

    const allDates = new Set();
    scenariosWithCurves.forEach((s) => {
      results[s.id].data.equityCurve.forEach((pt) => allDates.add(pt.date));
    });
    const sortedDates = [...allDates].sort();

    return sortedDates.map((date) => {
      const row = { date };
      scenariosWithCurves.forEach((s) => {
        const pt = results[s.id].data.equityCurve.find((p) => p.date === date);
        if (pt) row[s.name || s.id] = pt.value;
      });
      return row;
    });
  }, [scenarios, results]);

  const scenarioNames = scenarios
    .filter((s) => results[s.id]?.ok && results[s.id].data.equityCurve?.length > 0)
    .map((s) => s.name || s.id);

  const inputStyle = {
    padding: "6px 10px",
    background: colors.surfaceLight,
    border: `1px solid ${colors.border}`,
    borderRadius: 5,
    color: colors.text,
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 11,
  };

  const btnStyle = (accent) => ({
    padding: "8px 16px",
    background: accent ? colors.accent : "transparent",
    color: accent ? "#fff" : colors.textMuted,
    border: accent ? "none" : `1px solid ${colors.border}`,
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 12,
    fontFamily: "'JetBrains Mono', monospace",
    transition: "all 0.15s",
  });

  return (
    <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
      <SectionTitle subtitle="Backtest different index & ETF universes across different time periods" info="Define scenarios (tickers, dates), run batch backtests, compare results. Use Load to apply a scenario to the main dashboard.">
        Index & ETF Scenario Tester
      </SectionTitle>

      {/* Toolbar */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
        <button onClick={runAll} disabled={running} style={{ ...btnStyle(true), opacity: running ? 0.6 : 1, cursor: running ? "not-allowed" : "pointer" }}>
          {running ? "Running..." : "Run All Scenarios"}
        </button>
        <button onClick={addScenario} style={btnStyle(false)}>+ Add Scenario</button>
        <button onClick={loadPresets} style={btnStyle(false)}>Load Presets</button>
        {hasResults && (
          <button onClick={() => setShowEquity((v) => !v)} style={btnStyle(false)}>
            {showEquity ? "Hide Equity Curves" : "Show Equity Curves"}
          </button>
        )}
        {progress && (
          <span style={{ fontSize: 11, color: colors.textDim, marginLeft: "auto", fontFamily: "'JetBrains Mono', monospace" }}>
            {progress}
          </span>
        )}
      </div>

      {/* Scenario list (editable table) */}
      <div style={{ overflowX: "auto", marginBottom: 16 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
          <thead>
            <tr>
              {["#", "Name", "Tickers", "Start", "End", ""].map((h) => (
                <th key={h} style={{
                  padding: "8px 10px", textAlign: "left", borderBottom: `1px solid ${colors.border}`,
                  color: colors.textDim, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em",
                }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {scenarios.map((s, idx) => (
              <tr key={s.id} style={{ background: idx % 2 === 0 ? "transparent" : colors.surfaceLight }}>
                <td style={{ padding: "6px 10px", borderBottom: `1px solid ${colors.border}`, color: colors.textDim, width: 30 }}>{idx + 1}</td>
                <td style={{ padding: "6px 10px", borderBottom: `1px solid ${colors.border}`, width: 160 }}>
                  <input value={s.name} onChange={(e) => updateScenario(s.id, "name", e.target.value)} placeholder="Scenario name" style={{ ...inputStyle, width: "100%" }} />
                </td>
                <td style={{ padding: "6px 10px", borderBottom: `1px solid ${colors.border}`, minWidth: 220 }}>
                  <TickerSearch
                    value={s.tickers}
                    onChange={(arr) => updateScenario(s.id, "tickers", arr)}
                    placeholder="Search..."
                    compact
                  />
                </td>
                <td style={{ padding: "6px 10px", borderBottom: `1px solid ${colors.border}`, width: 130 }}>
                  <input type="date" value={s.startDate} onChange={(e) => updateScenario(s.id, "startDate", e.target.value)} style={{ ...inputStyle, width: "100%" }} />
                </td>
                <td style={{ padding: "6px 10px", borderBottom: `1px solid ${colors.border}`, width: 130 }}>
                  <input type="date" value={s.endDate} onChange={(e) => updateScenario(s.id, "endDate", e.target.value)} style={{ ...inputStyle, width: "100%" }} />
                </td>
                <td style={{ padding: "6px 10px", borderBottom: `1px solid ${colors.border}`, width: 30 }}>
                  <button onClick={() => removeScenario(s.id)}
                    style={{ background: "transparent", border: "none", color: colors.red, cursor: "pointer", fontSize: 14, padding: 2 }}
                    title="Remove scenario">
                    x
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Comparison results table */}
      {hasResults && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 10, color: colors.textDim, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 10, fontFamily: "'JetBrains Mono', monospace" }}>
            Results Comparison
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
              <thead>
                <tr>
                  {["Scenario", "Tickers", "Period", "Total Ret", "Ann. Ret", "Sharpe", "Max DD", "Volatility", "Status", ""].map((h) => (
                    <th key={h} style={{
                      padding: "8px 10px", textAlign: "left", borderBottom: `2px solid ${colors.border}`,
                      color: colors.textDim, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em", whiteSpace: "nowrap",
                    }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {scenarios.map((s, idx) => {
                  const r = results[s.id];
                  if (!r) return null;
                  const d = r.ok ? r.data : null;
                  const bestSharpe = Math.max(
                    ...scenarios.map((sc) => results[sc.id]?.ok ? results[sc.id].data.sharpe : -Infinity)
                  );
                  const isBest = d && d.sharpe >= bestSharpe - 0.001;
                  return (
                    <tr key={s.id} style={{ background: isBest ? colors.accentGlow : idx % 2 === 0 ? "transparent" : colors.surfaceLight }}>
                      <td style={{ padding: "8px 10px", borderBottom: `1px solid ${colors.border}`, fontWeight: isBest ? 700 : 400, color: isBest ? colors.accent : colors.text }}>
                        {s.name || `Scenario ${idx + 1}`} {isBest && "\u2605"}
                      </td>
                      <td style={{ padding: "8px 10px", borderBottom: `1px solid ${colors.border}`, color: colors.textMuted, fontSize: 10 }}>
                        {s.tickers.join(", ")}
                      </td>
                      <td style={{ padding: "8px 10px", borderBottom: `1px solid ${colors.border}`, color: colors.textMuted, fontSize: 10, whiteSpace: "nowrap" }}>
                        {s.startDate} \u2192 {s.endDate}
                      </td>
                      {r.ok ? (
                        <>
                          <td style={{ padding: "8px 10px", borderBottom: `1px solid ${colors.border}`, color: d.totalReturn >= 0 ? colors.green : colors.red }}>
                            {(d.totalReturn * 100).toFixed(2)}%
                          </td>
                          <td style={{ padding: "8px 10px", borderBottom: `1px solid ${colors.border}`, color: d.annualReturn >= 0 ? colors.green : colors.red }}>
                            {(d.annualReturn * 100).toFixed(2)}%
                          </td>
                          <td style={{ padding: "8px 10px", borderBottom: `1px solid ${colors.border}`, color: isBest ? colors.accent : colors.text, fontWeight: isBest ? 700 : 400 }}>
                            {d.sharpe.toFixed(3)}
                          </td>
                          <td style={{ padding: "8px 10px", borderBottom: `1px solid ${colors.border}`, color: colors.red }}>
                            {(d.maxDrawdown * 100).toFixed(2)}%
                          </td>
                          <td style={{ padding: "8px 10px", borderBottom: `1px solid ${colors.border}`, color: colors.orange }}>
                            {(d.volatility * 100).toFixed(2)}%
                          </td>
                          <td style={{ padding: "8px 10px", borderBottom: `1px solid ${colors.border}` }}>
                            <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 4, background: `${colors.green}20`, color: colors.green, border: `1px solid ${colors.green}40` }}>OK</span>
                          </td>
                          <td style={{ padding: "8px 10px", borderBottom: `1px solid ${colors.border}` }}>
                            {onLoadScenario && (
                              <button onClick={() => onLoadScenario({ tickers: s.tickers, startDate: s.startDate, endDate: s.endDate, backtestResult: { total_return: d.totalReturn, annual_return: d.annualReturn, sharpe_ratio: d.sharpe, max_drawdown: d.maxDrawdown, volatility: d.volatility, equity_curve: d.equityCurve.map(pt => ({ date: pt.date, portfolio_value: pt.value })) } })} style={{ fontSize: 10, padding: "3px 10px", borderRadius: 4, background: `${colors.accent}15`, color: colors.accent, border: `1px solid ${colors.accent}40`, cursor: "pointer", fontFamily: "'JetBrains Mono', monospace" }}>Load</button>
                            )}
                          </td>
                        </>
                      ) : (
                        <>
                          <td colSpan={5} style={{ padding: "8px 10px", borderBottom: `1px solid ${colors.border}`, color: colors.red, fontSize: 11 }}>
                            {r.error}
                          </td>
                          <td style={{ padding: "8px 10px", borderBottom: `1px solid ${colors.border}` }}>
                            <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 4, background: colors.redDim, color: colors.red, border: `1px solid ${colors.red}40` }}>ERR</span>
                          </td>
                          <td style={{ padding: "8px 10px", borderBottom: `1px solid ${colors.border}` }}></td>
                        </>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Equity curves overlay chart */}
      {showEquity && scenarioNames.length > 0 && (
        <div>
          <div style={{ fontSize: 10, color: colors.textDim, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 10, fontFamily: "'JetBrains Mono', monospace" }}>
            Equity Curves Overlay
          </div>
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={equityData()} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
              <XAxis dataKey="date" stroke={colors.textDim} tick={{ fontSize: 9 }} />
              <YAxis stroke={colors.textDim} tick={{ fontSize: 10 }} label={{ value: "Cumulative Value", angle: -90, position: "insideLeft", fill: colors.textDim, fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {scenarioNames.map((name, i) => (
                <Line
                  key={name}
                  type="monotone"
                  dataKey={name}
                  stroke={chartColors[i % chartColors.length]}
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export default React.memo(ScenarioTester);
