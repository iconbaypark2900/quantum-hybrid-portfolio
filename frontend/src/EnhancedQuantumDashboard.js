import React, { useState, useMemo, useCallback } from "react";
import { FaSun, FaMoon, FaStar, FaBook } from "react-icons/fa";
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { toast } from "react-toastify";
import { optimizePortfolio, optimizeBatch } from "./services/api";
import { darkTheme, lightTheme, chartColors, benchmarkColors, DashboardThemeContext } from "./theme";
import {
  generateMarketData, runEnhancedQSWOptimization, runBenchmarks,
  simulateEquityCurve, computeVaR,
} from "./lib/simulationEngine";
import {
  Slider, MetricCard, DataSourceBadge, TabButton, SectionTitle, SectionLabel, InfoBubble,
  RegimeSelector, EvolutionMethodSelector, CustomTooltip,
  TradeBlotter, BenchmarkComparison, BacktestPanel, DrawdownChart,
  CorrelationHeatmap, EfficientFrontier, WhatIfAdjuster, RegimeComparison,
  LoadingOverlay, ConfirmDialog, ScenarioTester, TickerSearch, HelpPanel,
} from "./components/dashboard";

const OBJECTIVE_TO_SIM = { max_sharpe: "balanced", min_variance: "conservative", risk_parity: "diversification", hrp: "balanced", target_return: "balanced" };
const STRESS_SECTOR_SHOCKS = {
  "2008 GFC":       { Tech: -0.45, Technology: -0.45, Finance: -0.60, Financials: -0.60, Energy: -0.40, Healthcare: -0.20, "Consumer Disc": -0.50, "Consumer Stpl": -0.15, Industrials: -0.45, Communication: -0.35, Materials: -0.40, Utilities: -0.25, "Real Estate": -0.40, Other: -0.35, Unknown: -0.35, "Broad Market": -0.50, International: -0.55, "Fixed Income": -0.05, Commodities: -0.20 },
  "COVID Crash":    { Tech: -0.25, Technology: -0.25, Finance: -0.35, Financials: -0.35, Energy: -0.55, Healthcare: -0.15, "Consumer Disc": -0.35, "Consumer Stpl": -0.10, Industrials: -0.35, Communication: -0.25, Materials: -0.30, Utilities: -0.20, "Real Estate": -0.25, Other: -0.30, Unknown: -0.30, "Broad Market": -0.34, International: -0.35, "Fixed Income": 0.02, Commodities: -0.25 },
  "2022 Rate Shock": { Tech: -0.30, Technology: -0.30, Finance: -0.15, Financials: -0.15, Energy: 0.20, Healthcare: -0.10, "Consumer Disc": -0.35, "Consumer Stpl": -0.05, Industrials: -0.15, Communication: -0.35, Materials: -0.10, Utilities: -0.05, "Real Estate": -0.25, Other: -0.15, Unknown: -0.15, "Broad Market": -0.25, International: -0.20, "Fixed Income": -0.15, Commodities: 0.10 },
  "Flash Crash":    { Tech: -0.08, Technology: -0.08, Finance: -0.10, Financials: -0.10, Energy: -0.07, Healthcare: -0.06, "Consumer Disc": -0.09, "Consumer Stpl": -0.04, Industrials: -0.08, Communication: -0.07, Materials: -0.07, Utilities: -0.03, "Real Estate": -0.06, Other: -0.07, Unknown: -0.07, "Broad Market": -0.09, International: -0.08, "Fixed Income": 0.01, Commodities: -0.05 },
};

// ─── MAIN DASHBOARD ───
export default function EnhancedQuantumDashboard() {
  // Theme state
  const [themeName, setThemeName] = useState(() => {
    try { return localStorage.getItem("dashboard_theme") || "dark"; } catch { return "dark"; }
  });
  const colors = themeName === "light" ? lightTheme : darkTheme;

  const toggleTheme = useCallback(() => {
    const next = themeName === "dark" ? "light" : "dark";
    setThemeName(next);
    try { localStorage.setItem("dashboard_theme", next); } catch { /* ignore */ }
  }, [themeName]);

  // Parameters
  const [nAssets, setNAssets] = useState(20);
  const [regime, setRegime] = useState("normal");
  const [omega, setOmega] = useState(0.30);
  const [evolutionTime, setEvolutionTime] = useState(10);
  const [maxWeight, setMaxWeight] = useState(0.10);
  const [turnoverLimit, setTurnoverLimit] = useState(0.20);
  const [dataSeed, setDataSeed] = useState(42);
  const [activeTab, setActiveTab] = useState("holdings");
  const [dataSource, setDataSource] = useState("simulation");
  const [tickers, setTickers] = useState(["AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","JPM","V","JNJ"]);
  const [startDate, setStartDate] = useState("2022-01-01");
  const [endDate, setEndDate] = useState("2024-01-01");
  const [evolutionMethod, setEvolutionMethod] = useState("continuous");
  const [objective, setObjective] = useState("max_sharpe");
  const [targetReturnPct, setTargetReturnPct] = useState(10);
  const [portfolioValue] = useState(100000);
  const [constraints] = useState({});

  const simObjective = OBJECTIVE_TO_SIM[objective] || "balanced";

  // Results
  const [apiResult, setApiResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [backtestResult, setBacktestResult] = useState(null);
  const [whatIfMetrics, setWhatIfMetrics] = useState(null);
  const [confirmAction, setConfirmAction] = useState(null);
  const [showHelp, setShowHelp] = useState(false);
  const [metricsView, setMetricsView] = useState("optimization");
  const [sensitivityData, setSensitivityData] = useState(null);
  const [sensitivityLoading, setSensitivityLoading] = useState(false);

  // Computed data
  const data = useMemo(() => dataSource === "simulation" ? generateMarketData(nAssets, 504, regime, dataSeed, tickers) : null, [nAssets, regime, dataSeed, dataSource, tickers]);
  const qsw = useMemo(() => (dataSource === "simulation" && data?.assets) ? runEnhancedQSWOptimization(data, omega, evolutionTime, maxWeight, turnoverLimit, evolutionMethod, simObjective) : null, [data, omega, evolutionTime, maxWeight, turnoverLimit, evolutionMethod, simObjective, dataSource]);
  const benchmarks = useMemo(() => (dataSource === "simulation" && data?.assets) ? runBenchmarks(data) : null, [data, dataSource]);
  const riskMetrics = useMemo(() => {
    if (dataSource === "simulation" && data && qsw?.weights) return computeVaR(data, qsw.weights, 0.95);
    if (dataSource === "api" && apiResult?.risk_metrics) return { var95: (apiResult.risk_metrics.var_95 || 0) * 100, cvar: (apiResult.risk_metrics.cvar || 0) * 100 };
    return { var95: 0, cvar: 0 };
  }, [data, qsw, dataSource, apiResult]);

  const equityCurves = useMemo(() => {
    if (dataSource !== "simulation" || !data || !qsw?.weights) return [{ day: 0, QSW: 100, "Equal Weight": 100, "Min Variance": 100, "Risk Parity": 100, "Max Sharpe": 100, "HRP": 100 }];
    const qswCurve = simulateEquityCurve(data, qsw.weights, 504);
    const ewCurve = simulateEquityCurve(data, benchmarks?.equalWeight?.weights || [], 504);
    const mvCurve = simulateEquityCurve(data, benchmarks?.minVariance?.weights || [], 504);
    const rpCurve = simulateEquityCurve(data, benchmarks?.riskParity?.weights || [], 504);
    const msCurve = simulateEquityCurve(data, benchmarks?.maxSharpe?.weights || [], 504);
    const hrpCurve = simulateEquityCurve(data, benchmarks?.hrp?.weights || [], 504);
    return qswCurve.map((pt, i) => ({ day: pt.day, QSW: pt.value, "Equal Weight": ewCurve[i]?.value || 100, "Min Variance": mvCurve[i]?.value || 100, "Risk Parity": rpCurve[i]?.value || 100, "Max Sharpe": msCurve[i]?.value || 100, "HRP": hrpCurve[i]?.value || 100 }));
  }, [data, qsw, benchmarks, dataSource]);

  const holdings = useMemo(() => {
    if (dataSource === "simulation" && data?.assets && qsw?.weights) {
      return data.assets.map((a, i) => ({ name: a.name, sector: a.sector, weight: qsw.weights[i] || 0, annReturn: a.annReturn, annVol: a.annVol, sharpe: a.sharpe })).filter(h => h.weight > 0.005).sort((a, b) => b.weight - a.weight);
    }
    return apiResult?.holdings || [];
  }, [data, qsw, apiResult, dataSource]);

  const sectorData = useMemo(() => {
    if (!holdings?.length) return [];
    const sectors = {};
    holdings.forEach(h => { sectors[h.sector || "Unknown"] = (sectors[h.sector || "Unknown"] || 0) + (h.weight || 0); });
    return Object.entries(sectors).map(([name, value]) => ({ name, value: Math.round(value * 1000) / 10 })).sort((a, b) => b.value - a.value);
  }, [holdings]);

  const benchmarkComparison = useMemo(() => {
    if (dataSource === "api" && apiResult?.benchmarks) {
      const bm = apiResult.benchmarks;
      const rows = [
        { name: "QSW", sharpe: apiResult.qsw_result?.sharpe_ratio || apiResult.qsw_result?.sharpe || 0, return: (apiResult.qsw_result?.expected_return || apiResult.qsw_result?.portReturn || 0) * 100, vol: (apiResult.qsw_result?.volatility || apiResult.qsw_result?.portVol || 0) * 100, nActive: apiResult.qsw_result?.n_active || apiResult.qsw_result?.nActive || 0 },
      ];
      if (bm.equal_weight) rows.push({ name: "Equal Wt", sharpe: bm.equal_weight.sharpe_ratio || bm.equal_weight.sharpe || 0, return: (bm.equal_weight.expected_return || 0) * 100, vol: (bm.equal_weight.volatility || 0) * 100, nActive: bm.equal_weight.n_active || nAssets });
      if (bm.min_variance) rows.push({ name: "Min Var", sharpe: bm.min_variance.sharpe_ratio || bm.min_variance.sharpe || 0, return: (bm.min_variance.expected_return || 0) * 100, vol: (bm.min_variance.volatility || 0) * 100, nActive: bm.min_variance.n_active || nAssets });
      if (bm.risk_parity) rows.push({ name: "Risk Par", sharpe: bm.risk_parity.sharpe_ratio || bm.risk_parity.sharpe || 0, return: (bm.risk_parity.expected_return || 0) * 100, vol: (bm.risk_parity.volatility || 0) * 100, nActive: bm.risk_parity.n_active || nAssets });
      if (bm.max_sharpe) rows.push({ name: "Max Shp", sharpe: bm.max_sharpe.sharpe_ratio || bm.max_sharpe.sharpe || 0, return: (bm.max_sharpe.expected_return || 0) * 100, vol: (bm.max_sharpe.volatility || 0) * 100, nActive: bm.max_sharpe.n_active || nAssets });
      if (bm.hrp) rows.push({ name: "HRP", sharpe: bm.hrp.sharpe_ratio || bm.hrp.sharpe || 0, return: (bm.hrp.expected_return || 0) * 100, vol: (bm.hrp.volatility || 0) * 100, nActive: bm.hrp.n_active || nAssets });
      return rows;
    }
    return [
      { name: "QSW", sharpe: qsw?.sharpe || 0, return: (qsw?.portReturn || 0) * 100, vol: (qsw?.portVol || 0) * 100, nActive: qsw?.nActive || 0 },
      { name: "Equal Wt", sharpe: benchmarks?.equalWeight?.sharpe || 0, return: (benchmarks?.equalWeight?.portReturn || 0) * 100, vol: (benchmarks?.equalWeight?.portVol || 0) * 100, nActive: nAssets },
      { name: "Min Var", sharpe: benchmarks?.minVariance?.sharpe || 0, return: (benchmarks?.minVariance?.portReturn || 0) * 100, vol: (benchmarks?.minVariance?.portVol || 0) * 100, nActive: nAssets },
      { name: "Risk Par", sharpe: benchmarks?.riskParity?.sharpe || 0, return: (benchmarks?.riskParity?.portReturn || 0) * 100, vol: (benchmarks?.riskParity?.portVol || 0) * 100, nActive: nAssets },
      { name: "Max Shp", sharpe: benchmarks?.maxSharpe?.sharpe || 0, return: (benchmarks?.maxSharpe?.portReturn || 0) * 100, vol: (benchmarks?.maxSharpe?.portVol || 0) * 100, nActive: nAssets },
      { name: "HRP", sharpe: benchmarks?.hrp?.sharpe || 0, return: (benchmarks?.hrp?.portReturn || 0) * 100, vol: (benchmarks?.hrp?.portVol || 0) * 100, nActive: nAssets },
    ];
  }, [qsw, benchmarks, nAssets, dataSource, apiResult]);

  const omegaSensitivity = useMemo(() => {
    if (!data?.assets?.length) return [];
    const pts = [];
    for (let o = 0.05; o <= 0.60; o += 0.025) {
      try { const r = runEnhancedQSWOptimization(data, o, evolutionTime, maxWeight, turnoverLimit, evolutionMethod, simObjective); if (r && typeof r.sharpe === "number") pts.push({ omega: o.toFixed(2), sharpe: r.sharpe, return: (r.portReturn || 0) * 100, vol: (r.portVol || 0) * 100, nActive: r.nActive || 0 }); } catch { /* skip */ }
    }
    return pts;
  }, [data, evolutionTime, maxWeight, turnoverLimit, evolutionMethod, simObjective]);

  const evolSensitivity = useMemo(() => {
    if (!data?.assets?.length) return [];
    const pts = [];
    for (let t = 1; t <= 50; t += 2) {
      try { const r = runEnhancedQSWOptimization(data, omega, t, maxWeight, turnoverLimit, evolutionMethod, simObjective); if (r && typeof r.sharpe === "number") pts.push({ time: t, sharpe: r.sharpe, nActive: r.nActive || 0 }); } catch { /* skip */ }
    }
    return pts;
  }, [data, omega, maxWeight, turnoverLimit, evolutionMethod, simObjective]);

  const corrData = useMemo(() => {
    if (dataSource === "api" && apiResult?.correlation_matrix) {
      const cm = apiResult.correlation_matrix;
      const names = apiResult.assets?.map(a => a.name || a) || Object.keys(cm);
      const top = names.slice(0, 10);
      return top.map(n => { const row = { name: n }; top.forEach((n2, j) => { row[n2] = cm[names.indexOf(n)]?.[j] ?? 0; }); return row; });
    }
    if (!holdings?.length || !data?.assets || !data?.corr) return [];
    const topIdx = holdings.slice(0, 10).map(h => data.assets.findIndex(a => a.name === h.name)).filter(idx => idx >= 0 && idx < data.assets.length);
    if (!topIdx.length) return [];
    return topIdx.map((i) => {
      if (i < 0 || i >= data.assets.length || !data.assets[i]) return null;
      const row = { name: data.assets[i].name };
      topIdx.forEach((j) => { const cn = data.assets[j]?.name; if (cn) row[cn] = data.corr[i]?.[j] ?? 0; });
      return row;
    }).filter(Boolean);
  }, [holdings, data, dataSource, apiResult]);

  let bestBenchmarkSharpe = 0;
  if (dataSource === "api" && apiResult?.benchmarks) {
    const bm = apiResult.benchmarks;
    bestBenchmarkSharpe = Math.max(
      bm.equal_weight?.sharpe_ratio || bm.equal_weight?.sharpe || 0,
      bm.min_variance?.sharpe_ratio || bm.min_variance?.sharpe || 0,
      bm.risk_parity?.sharpe_ratio || bm.risk_parity?.sharpe || 0,
      bm.max_sharpe?.sharpe_ratio || bm.max_sharpe?.sharpe || 0,
      bm.hrp?.sharpe_ratio || bm.hrp?.sharpe || 0,
    );
  } else if (benchmarks) {
    bestBenchmarkSharpe = Math.max(benchmarks.equalWeight?.sharpe || 0, benchmarks.minVariance?.sharpe || 0, benchmarks.riskParity?.sharpe || 0, benchmarks.maxSharpe?.sharpe || 0, benchmarks.hrp?.sharpe || 0);
  }
  const sharpeImprovement = bestBenchmarkSharpe === 0 ? 0 : ((qsw?.sharpe || 0) / bestBenchmarkSharpe - 1) * 100;

  const runOptimization = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { tickers, startDate, endDate, regime, omega, evolutionTime, maxWeight, turnoverLimit, objective, strategyPreset: "balanced", constraints };
      if (objective === "target_return") params.targetReturn = targetReturnPct / 100;
      const result = await optimizePortfolio(params);
      setApiResult(result);
      toast.success("Optimization complete");
    } catch (err) {
      setError(err.message);
      toast.error(`Optimization failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleResetParams = () => {
    setConfirmAction({
      title: "Reset Parameters",
      message: "Reset all parameters to their default values? This will clear any custom settings.",
      onConfirm: () => {
        setOmega(0.30); setEvolutionTime(10); setMaxWeight(0.10); setTurnoverLimit(0.20); setNAssets(20); setRegime("normal"); setDataSeed(42); setEvolutionMethod("continuous"); setObjective("max_sharpe"); setTargetReturnPct(10); setBacktestResult(null); setTickers(["AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","JPM","V","JNJ"]); setStartDate("2022-01-01"); setEndDate("2024-01-01"); setMetricsView("optimization");
        setConfirmAction(null);
        toast.info("Parameters reset to defaults");
      },
    });
  };

  const handleWhatIfWeightsChanged = useCallback((newWeights) => {
    if (data?.assets && newWeights?.length > 0) {
      let portReturn = 0, portVar = 0;
      for (let i = 0; i < newWeights.length; i++) {
        portReturn += (newWeights[i] || 0) * (data.assets[i]?.annReturn || 0);
        for (let j = 0; j < newWeights.length; j++) portVar += (newWeights[i] || 0) * (newWeights[j] || 0) * (data.corr?.[i]?.[j] || 0) * (data.assets[i]?.annVol || 0) * (data.assets[j]?.annVol || 0);
      }
      const portVol = Math.sqrt(Math.max(0, portVar));
      setWhatIfMetrics({ sharpe: portVol > 0 ? portReturn / portVol : 0, portReturn, portVol, nActive: newWeights.filter(w => w > 0.005).length });
    } else {
      setWhatIfMetrics(null);
    }
  }, [data]);

  const currentResult = dataSource === "api" ? apiResult : { qsw_result: qsw };
  const cs = currentResult?.qsw_result; // shorthand

  return (
    <DashboardThemeContext.Provider value={colors}>
      <div style={{ background: colors.bg, minHeight: "100vh", color: colors.text, fontFamily: "'Space Grotesk', -apple-system, sans-serif" }}>

        {/* Confirm dialog */}
        {confirmAction && <ConfirmDialog title={confirmAction.title} message={confirmAction.message} onConfirm={confirmAction.onConfirm} onCancel={() => setConfirmAction(null)} />}
        {showHelp && <HelpPanel onClose={() => setShowHelp(false)} />}

        {/* ─── HEADER ─── */}
        <div style={{ borderBottom: `1px solid ${colors.border}`, padding: "12px 24px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: `linear-gradient(135deg, ${colors.accent}, ${colors.purple})`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 17, fontWeight: 700, color: "#fff", boxShadow: `0 0 16px ${colors.accent}40` }}>{"⟨ψ⟩"}</div>
            <div>
              <div style={{ fontSize: 17, fontWeight: 800, letterSpacing: "-0.03em", background: `linear-gradient(135deg, ${colors.text}, ${colors.accent})`, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Quantum Portfolio Lab</div>
              <div style={{ fontSize: 10, color: colors.textDim, display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>QSW-Inspired Optimization Engine <span style={{ fontSize: 9, padding: "1px 6px", borderRadius: 4, background: `${colors.green}20`, color: colors.green, border: `1px solid ${colors.green}40`, fontFamily: "'JetBrains Mono', monospace" }}>v2.0</span> <span style={{ fontSize: 8, color: colors.textDim, fontFamily: "'JetBrains Mono', monospace" }} title="Research-backed methods: Hierarchical Risk Parity (L&oacute;pez de Prado, 2016), Ledoit&ndash;Wolf shrinkage covariance">HRP &middot; Ledoit&ndash;Wolf &middot; Research-Backed</span></div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
            <div style={{ display: "flex", gap: 4, background: colors.surface, borderRadius: 8, padding: 3, border: `1px solid ${colors.border}` }}>
              <TabButton active={dataSource === "simulation"} onClick={() => setDataSource("simulation")}>Simulation</TabButton>
              <TabButton active={dataSource === "api"} onClick={() => setDataSource("api")}>Live API</TabButton>
            </div>
            <DataSourceBadge source={dataSource} />
          </div>
          <div style={{ display: "flex", gap: 3, background: colors.surface, borderRadius: 8, padding: 3, border: `1px solid ${colors.border}` }}>
            <TabButton active={activeTab === "holdings"} onClick={() => setActiveTab("holdings")}>Holdings</TabButton>
            <TabButton active={activeTab === "performance"} onClick={() => setActiveTab("performance")}>Performance</TabButton>
            <TabButton active={activeTab === "risk"} onClick={() => setActiveTab("risk")}>Risk</TabButton>
            <TabButton active={activeTab === "analysis"} onClick={() => setActiveTab("analysis")}>Analysis</TabButton>
            <TabButton active={activeTab === "sensitivity"} onClick={() => setActiveTab("sensitivity")}>Sensitivity</TabButton>
            <TabButton active={activeTab === "scenarios"} onClick={() => setActiveTab("scenarios")}>Scenarios</TabButton>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {/* Help / Documentation */}
            <button onClick={() => setShowHelp(true)} title="Help & Documentation"
              style={{ padding: "6px 12px", background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 6, color: colors.textMuted, fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontFamily: "'JetBrains Mono', monospace" }}>
              <FaBook size={14} /> Help
            </button>
            {/* Theme toggle */}
            <button onClick={toggleTheme} title={`Switch to ${themeName === "dark" ? "light" : "dark"} theme`}
              style={{ padding: "6px 12px", background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 6, color: colors.textMuted, fontSize: 14, cursor: "pointer" }}>
              {themeName === "dark" ? <FaSun size={14} /> : <FaMoon size={14} />}
            </button>
            {/* Export button */}
            <button onClick={() => {
              const exportData = { timestamp: new Date().toISOString(), source: dataSource, parameters: { omega, evolutionTime, maxWeight, turnoverLimit, regime, evolutionMethod, objective }, qsw_result: cs || null, holdings: holdings || [], sectorAllocation: sectorData || [], riskMetrics: riskMetrics || {}, backtestResult: backtestResult || null };
              const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a"); a.href = url; a.download = `quantum-portfolio-${new Date().toISOString().slice(0, 10)}.json`; a.click(); URL.revokeObjectURL(url);
              toast.success("Portfolio exported");
            }} style={{ padding: "8px 14px", background: "transparent", border: `1px solid ${colors.border}`, borderRadius: 6, color: colors.textMuted, fontSize: 12, cursor: "pointer", fontFamily: "'JetBrains Mono', monospace" }} title="Export portfolio data as JSON">Export</button>
          </div>
        </div>

        <div style={{ display: "flex", height: "calc(100vh - 65px)" }}>

          {/* ─── LEFT PANEL: CONTROLS ─── */}
          <div style={{ width: 280, borderRight: `1px solid ${colors.border}`, padding: 20, overflowY: "auto", flexShrink: 0 }}>
            <SectionLabel title="Quantum Parameters" info="Core QSW algorithm settings: omega tunes quantum vs classical coupling; evolution time controls walk diffusion." />
            <Slider label="Omega (ω)" value={omega} onChange={setOmega} min={0.05} max={0.60} step={0.01} info="Mixing parameter: quantum potential vs. graph coupling" />
            <Slider label="Evolution Time" value={evolutionTime} onChange={setEvolutionTime} min={1} max={50} step={1} info="Higher = more smoothing, lower = more differentiation" />
            <div style={{ height: 1, background: colors.border, margin: "16px 0" }} />
            <SectionLabel title="Market Regime" info="Simulated market conditions: normal, bull, bear, or volatile. Affects returns, volatility, and correlation structure." />
            <RegimeSelector value={regime} onChange={setRegime} />
            <div style={{ height: 1, background: colors.border, margin: "16px 0" }} />
            <SectionLabel title="Evolution Method" info="Quantum walk dynamics: continuous, discrete, decoherent, adiabatic, or variational. Each models diffusion differently." />
            <EvolutionMethodSelector value={evolutionMethod} onChange={setEvolutionMethod} />
            <div style={{ height: 1, background: colors.border, margin: "16px 0" }} />
            <SectionLabel title="Objective" info="Optimization target: Max Sharpe (risk-adjusted return), Min Variance, Risk Parity, HRP (hierarchical clustering), or Target Return." />
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 8 }}>
              {[
                { key: "max_sharpe", label: "Max Sharpe" },
                { key: "min_variance", label: "Min Variance" },
                { key: "risk_parity", label: "Risk Parity" },
                { key: "hrp", label: "HRP" },
                { key: "target_return", label: "Target Ret" },
              ].map(o => (
                <button key={o.key} onClick={() => setObjective(o.key)} style={{
                  flex: "1 1 auto", padding: "6px 8px", fontSize: 10,
                  background: objective === o.key ? `${colors.accent}20` : "transparent",
                  border: `1px solid ${objective === o.key ? colors.accent : colors.border}`,
                  borderRadius: 5, color: objective === o.key ? colors.accent : colors.textDim,
                  cursor: "pointer", fontFamily: "'JetBrains Mono', monospace", transition: "all 0.2s",
                }}>{o.label}</button>
              ))}
            </div>
            {objective === "hrp" && (
              <div style={{ marginBottom: 8, fontSize: 9, color: colors.green, fontStyle: "italic" }}>
                Hierarchical Risk Parity &mdash; Ledoit&ndash;Wolf covariance
              </div>
            )}
            {objective === "target_return" && (
              <div style={{ marginBottom: 8 }}>
                <label style={{ display: "block", fontSize: 11, color: colors.textMuted, marginBottom: 4 }}>Target Annual Return (%)</label>
                <input type="number" min={1} max={50} step={0.5} value={targetReturnPct}
                  onChange={e => setTargetReturnPct(Math.max(0.5, Math.min(50, parseFloat(e.target.value) || 0)))}
                  style={{ width: "100%", padding: "6px 10px", background: colors.surfaceLight, border: `1px solid ${colors.border}`, borderRadius: 5, color: colors.text, fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}
                />
              </div>
            )}
            <div style={{ height: 1, background: colors.border, margin: "16px 0" }} />
            <SectionLabel title="Constraints" info="Portfolio constraints: max weight per position, turnover limit, and universe size." />
            <Slider label="Max Weight" value={maxWeight} onChange={setMaxWeight} min={0.03} max={0.30} step={0.01} unit="%" info="Maximum allocation per position" />
            <Slider label="Max Turnover" value={turnoverLimit} onChange={setTurnoverLimit} min={0.05} max={0.50} step={0.01} info="Maximum portfolio turnover per rebalance" />
            <Slider label="Universe Size" value={nAssets} onChange={setNAssets} min={5} max={30} step={1} unit=" assets" info="Number of assets in investable universe" />
            <div style={{ height: 1, background: colors.border, margin: "16px 0" }} />
            <SectionLabel title="Tickers & Dates" info="Select tickers (search/autocomplete) and backtest date range. Used for both API optimization and simulation." />
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", fontSize: 12, color: colors.textMuted, marginBottom: 6 }}>Tickers</label>
              <TickerSearch value={tickers} onChange={setTickers} placeholder="Search tickers..." />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
              <div>
                <label style={{ display: "block", fontSize: 11, color: colors.textMuted, marginBottom: 4 }}>Start</label>
                <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} style={{ width: "100%", padding: "6px 8px", background: colors.surfaceLight, border: `1px solid ${colors.border}`, borderRadius: 5, color: colors.text, fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }} />
              </div>
              <div>
                <label style={{ display: "block", fontSize: 11, color: colors.textMuted, marginBottom: 4 }}>End</label>
                <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} style={{ width: "100%", padding: "6px 8px", background: colors.surfaceLight, border: `1px solid ${colors.border}`, borderRadius: 5, color: colors.text, fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }} />
              </div>
            </div>
            {dataSource === "api" && (
              <>
                <div style={{ position: "relative" }}>
                  <button onClick={runOptimization} disabled={loading} style={{ width: "100%", padding: "10px", backgroundColor: colors.accent, color: "white", border: "none", borderRadius: 6, cursor: loading ? "not-allowed" : "pointer", marginBottom: 12 }}>{loading ? "Optimizing..." : "Run Optimization"}</button>
                  {loading && <LoadingOverlay message="Optimizing portfolio..." />}
                </div>
                {error && <div style={{ color: colors.red, padding: "10px", background: colors.redDim, borderRadius: 6, fontSize: 12, marginBottom: 8 }}>Error: {error}</div>}
              </>
            )}
            <div style={{ height: 1, background: colors.border, margin: "16px 0" }} />
            <SectionLabel title="Simulation" info="Random seed controls scenario generation. Change to explore different synthetic market paths." />
            <Slider label="Random Seed" value={dataSeed} onChange={setDataSeed} min={1} max={999} step={1} info="Change to generate different market scenarios" />
            <button onClick={handleResetParams} style={{ width: "100%", padding: "8px 0", background: "transparent", border: `1px solid ${colors.border}`, borderRadius: 6, color: colors.textMuted, fontSize: 11, cursor: "pointer", marginTop: 8, fontFamily: "'JetBrains Mono', monospace" }}>Reset All Parameters</button>
            <div style={{ marginTop: 16, padding: 12, background: colors.surfaceLight, borderRadius: 8, border: `1px solid ${colors.border}` }}>
              <div style={{ fontSize: 9, color: colors.textDim, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>Portfolio Status <InfoBubble info="Current optimization summary: Sharpe, return, volatility, and active positions." size={9} /></div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontSize: 11 }}>
                <div style={{ color: colors.textMuted }}>Sharpe</div><div style={{ color: colors.accent, textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontWeight: 600 }}>{(cs?.sharpe || cs?.sharpe_ratio || 0).toFixed(3)}</div>
                <div style={{ color: colors.textMuted }}>Return</div><div style={{ color: colors.green, textAlign: "right", fontFamily: "'JetBrains Mono', monospace" }}>{((cs?.portReturn || cs?.expected_return || 0) * 100).toFixed(1)}%</div>
                <div style={{ color: colors.textMuted }}>Vol</div><div style={{ color: colors.orange, textAlign: "right", fontFamily: "'JetBrains Mono', monospace" }}>{((cs?.portVol || cs?.volatility || 0) * 100).toFixed(1)}%</div>
                <div style={{ color: colors.textMuted }}>Positions</div><div style={{ color: colors.purple, textAlign: "right", fontFamily: "'JetBrains Mono', monospace" }}>{cs?.nActive || holdings?.length || 0}</div>
              </div>
            </div>
          </div>

          {/* ─── MAIN CONTENT ─── */}
          <div style={{ flex: 1, overflowY: "auto", padding: 24 }}>
            {/* Metric Cards */}
            <div style={{ marginBottom: 24 }}>
              {backtestResult && (
                <div style={{ display: "flex", gap: 4, marginBottom: 10 }}>
                  {[{ key: "optimization", label: "Optimization" }, { key: "backtest", label: "Backtest" }].map(v => (
                    <button key={v.key} onClick={() => setMetricsView(v.key)} style={{
                      padding: "4px 12px", fontSize: 10, borderRadius: 4,
                      background: metricsView === v.key ? `${colors.accent}20` : "transparent",
                      border: `1px solid ${metricsView === v.key ? colors.accent : colors.border}`,
                      color: metricsView === v.key ? colors.accent : colors.textDim,
                      cursor: "pointer", fontFamily: "'JetBrains Mono', monospace",
                    }}>{v.label}</button>
                  ))}
                </div>
              )}
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                {metricsView === "backtest" && backtestResult ? (<>
                  <MetricCard label="Sharpe Ratio" value={(backtestResult.sharpe_ratio ?? 0).toFixed(3)} color={colors.accent} description="Backtest" info="Risk-adjusted return: excess return per unit of volatility." />
                  <MetricCard label="Annual Return" value={((backtestResult.annual_return ?? 0) * 100).toFixed(1)} unit="%" color={(backtestResult.annual_return ?? 0) >= 0 ? colors.green : colors.red} description="Backtest" info="Annualized return over the backtest period." />
                  <MetricCard label="Total Return" value={((backtestResult.total_return ?? 0) * 100).toFixed(1)} unit="%" color={(backtestResult.total_return ?? 0) >= 0 ? colors.green : colors.red} description="Backtest" info="Cumulative return from start to end of backtest." />
                  <MetricCard label="Max Drawdown" value={((backtestResult.max_drawdown ?? 0) * 100).toFixed(1)} unit="%" color={colors.red} description="Backtest" info="Largest peak-to-trough decline during the backtest." />
                  <MetricCard label="Volatility" value={((backtestResult.volatility ?? 0) * 100).toFixed(1)} unit="%" color={colors.orange} description="Backtest" info="Annualized standard deviation of returns." />
                </>) : (<>
                  <MetricCard label="Sharpe Ratio" value={(cs?.sharpe ?? cs?.sharpe_ratio ?? 0).toFixed(3)} color={(cs?.sharpe || 0) > bestBenchmarkSharpe ? colors.green : colors.orange} delta={sharpeImprovement} description="Risk-adjusted return" info="Excess return per unit of volatility. Higher is better." />
                  <MetricCard label="Expected Return" value={((cs?.portReturn ?? cs?.expected_return ?? 0) * 100).toFixed(1)} unit="%" color={colors.accent} description="Annualized" info="Annualized expected portfolio return." />
                  <MetricCard label="Volatility" value={((cs?.portVol ?? cs?.volatility ?? 0) * 100).toFixed(1)} unit="%" color={colors.orange} description="Annualized" info="Annualized standard deviation of portfolio returns." />
                  <MetricCard label="Active Positions" value={cs?.nActive ?? 0} unit={`/ ${nAssets}`} color={colors.purple} description="Above 0.5% weight" info="Number of positions with weight above 0.5%." />
                  <MetricCard label="Daily VaR (95%)" value={(riskMetrics?.var95 ?? 0).toFixed(2)} unit="%" color={colors.red} description="Max daily loss at 95% CI" info="95% Value at Risk: max daily loss expected with 95% confidence." />
                </>)}
              </div>
            </div>

            {/* ─── HOLDINGS TAB ─── */}
            {activeTab === "holdings" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
                  <SectionTitle subtitle={`${holdings?.length || 0} positions above 0.5%`} info="Optimized weights from QSW. Toggle Optimization vs Backtest above to compare.">Portfolio Holdings</SectionTitle>
                  <div style={{ maxHeight: 380, overflowY: "auto" }}>
                    {holdings?.length > 0 ? holdings.map((h, i) => {
                      const weightPct = maxWeight > 0 ? Math.min((h.weight / maxWeight) * 100, 100) : 0;
                      return (
                        <div key={h.name || i} style={{ display: "flex", alignItems: "center", padding: "6px 0", borderBottom: `1px solid ${colors.border}`, gap: 10 }}>
                          <span style={{ width: 18, fontSize: 10, color: colors.textDim, fontFamily: "'JetBrains Mono', monospace" }}>{i + 1}</span>
                          <div style={{ flex: 1 }}><span style={{ fontSize: 13, fontWeight: 600, color: colors.text }}>{h.name}</span><span style={{ fontSize: 10, color: colors.textDim, marginLeft: 6 }}>{h.sector}</span></div>
                          <div style={{ width: 80 }}><div style={{ height: 4, background: colors.border, borderRadius: 2, overflow: "hidden" }}><div style={{ height: "100%", width: `${weightPct}%`, background: chartColors[i % chartColors.length], borderRadius: 2 }} /></div></div>
                          <span style={{ width: 50, textAlign: "right", fontSize: 12, fontWeight: 600, color: colors.accent, fontFamily: "'JetBrains Mono', monospace" }}>{(h.weight * 100).toFixed(1)}%</span>
                        </div>
                      );
                    }) : <div style={{ padding: 40, textAlign: "center", color: colors.textDim }}>No holdings data available</div>}
                  </div>
                </div>
                <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
                  <SectionTitle subtitle="Allocation by GICS sector" info="Portfolio allocation by industry sector (GICS classification).">Sector Breakdown</SectionTitle>
                  {sectorData?.length > 0 ? (
                    <ResponsiveContainer width="100%" height={300}><PieChart><Pie data={sectorData} cx="50%" cy="50%" innerRadius={60} outerRadius={110} dataKey="value" nameKey="name" stroke={colors.bg} strokeWidth={2}>{sectorData.map((_, i) => <Cell key={i} fill={chartColors[i % chartColors.length]} />)}</Pie><Tooltip content={<CustomTooltip />} /><Legend wrapperStyle={{ fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }} /></PieChart></ResponsiveContainer>
                  ) : <div style={{ height: 300, display: "flex", alignItems: "center", justifyContent: "center", color: colors.textDim }}>No sector data available</div>}
                </div>
                <div style={{ gridColumn: "1 / -1" }}><TradeBlotter holdings={holdings} portfolioValue={portfolioValue} /></div>
                <div style={{ gridColumn: "1 / -1" }}><BenchmarkComparison apiResult={apiResult} simData={data} simBenchmarks={benchmarks} simQswWeights={qsw?.weights} /></div>
              </div>
            )}

            {/* ─── PERFORMANCE TAB ─── */}
            {activeTab === "performance" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 20 }}>
                <BacktestPanel tickers={tickers} startDate={startDate} endDate={endDate} objective={objective} targetReturn={objective === "target_return" ? targetReturnPct / 100 : undefined} strategyPreset="balanced" constraints={constraints} onBacktestComplete={(r) => { setBacktestResult(r); setMetricsView("backtest"); toast.success("Backtest complete"); }} />
                <DrawdownChart backtestResult={backtestResult} />
                <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
                  <SectionTitle subtitle={backtestResult?.equity_curve?.length > 0 ? "Historical backtest equity curve" : "Simulated 2-year equity curve starting at $100"} info="Equity curve shows portfolio value over time. Backtest uses real history; simulation uses synthetic data.">Cumulative Performance</SectionTitle>
                  {backtestResult?.equity_curve?.length > 0 ? (
                    <ResponsiveContainer width="100%" height={350}>
                      <LineChart data={backtestResult.equity_curve} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke={colors.border} /><XAxis dataKey="date" stroke={colors.textDim} tick={{ fontSize: 10 }} /><YAxis stroke={colors.textDim} tick={{ fontSize: 10 }} label={{ value: "Portfolio Value", angle: -90, position: "insideLeft", fill: colors.textDim, fontSize: 11 }} /><Tooltip content={<CustomTooltip />} /><Legend wrapperStyle={{ fontSize: 11 }} />
                        <Line type="monotone" dataKey="portfolio_value" stroke={colors.accent} strokeWidth={2.5} dot={false} name="Backtest" />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : equityCurves?.length > 1 ? (
                    <ResponsiveContainer width="100%" height={350}>
                      <LineChart data={equityCurves} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke={colors.border} /><XAxis dataKey="day" stroke={colors.textDim} tick={{ fontSize: 10 }} label={{ value: "Trading Days", position: "bottom", fill: colors.textDim, fontSize: 11 }} /><YAxis stroke={colors.textDim} tick={{ fontSize: 10 }} label={{ value: "Portfolio Value ($)", angle: -90, position: "insideLeft", fill: colors.textDim, fontSize: 11 }} /><Tooltip content={<CustomTooltip />} /><Legend wrapperStyle={{ fontSize: 11 }} /><ReferenceLine y={100} stroke={colors.textDim} strokeDasharray="3 3" />
                        <Line type="monotone" dataKey="QSW" stroke={benchmarkColors.QSW} strokeWidth={2.5} dot={false} /><Line type="monotone" dataKey="Equal Weight" stroke={benchmarkColors["Equal Weight"]} strokeWidth={1.5} dot={false} strokeDasharray="4 2" /><Line type="monotone" dataKey="Min Variance" stroke={benchmarkColors["Min Variance"]} strokeWidth={1.5} dot={false} strokeDasharray="4 2" /><Line type="monotone" dataKey="Risk Parity" stroke={benchmarkColors["Risk Parity"]} strokeWidth={1.5} dot={false} strokeDasharray="4 2" /><Line type="monotone" dataKey="Max Sharpe" stroke={benchmarkColors["Max Sharpe"]} strokeWidth={1.5} dot={false} strokeDasharray="4 2" /><Line type="monotone" dataKey="HRP" stroke={benchmarkColors["HRP"]} strokeWidth={1.8} dot={false} strokeDasharray="6 3" />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : <div style={{ height: 350, display: "flex", alignItems: "center", justifyContent: "center", color: colors.textDim }}>Run a backtest or switch to simulation mode to see equity curves</div>}
                </div>
                <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
                  <SectionTitle subtitle="Side-by-side comparison of all strategies" info="QSW vs benchmarks: Max Sharpe, Min Variance, Risk Parity, HRP, Equal Weight. Star = best Sharpe.">Strategy Comparison</SectionTitle>
                  {benchmarkComparison?.length > 0 ? (<>
                    <ResponsiveContainer width="100%" height={280}><BarChart data={benchmarkComparison} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}><CartesianGrid strokeDasharray="3 3" stroke={colors.border} /><XAxis dataKey="name" stroke={colors.textDim} tick={{ fontSize: 11 }} /><YAxis stroke={colors.textDim} tick={{ fontSize: 10 }} /><Tooltip content={<CustomTooltip />} /><Legend wrapperStyle={{ fontSize: 11 }} /><Bar dataKey="sharpe" name="Sharpe" fill={colors.accent} radius={[4, 4, 0, 0]} /><Bar dataKey="return" name="Return (%)" fill={colors.green} radius={[4, 4, 0, 0]} /><Bar dataKey="vol" name="Vol (%)" fill={colors.orange} radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer>
                    <div style={{ marginTop: 16, overflowX: "auto" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
                        <thead><tr>{["Strategy", "Sharpe", "Return", "Volatility", "Positions"].map(h => <th key={h} style={{ padding: "8px 12px", textAlign: "left", borderBottom: `1px solid ${colors.border}`, color: colors.textDim, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</th>)}</tr></thead>
                        <tbody>{benchmarkComparison.map((b, i) => { const isQSW = b.name === "QSW"; const maxS = Math.max(...benchmarkComparison.map(x => x.sharpe || 0)); const isBest = (b.sharpe || 0) >= maxS - 0.001; return (<tr key={b.name || i} style={{ background: isQSW ? colors.accentGlow : "transparent" }}><td style={{ padding: "8px 12px", borderBottom: `1px solid ${colors.border}`, fontWeight: isQSW ? 700 : 400, color: isQSW ? colors.accent : colors.text }}>{b.name} {isBest && <FaStar size={12} style={{ color: colors.accent, display: "inline", verticalAlign: "middle" }} />}</td><td style={{ padding: "8px 12px", borderBottom: `1px solid ${colors.border}`, color: isBest ? colors.green : colors.text }}>{(b.sharpe || 0).toFixed(3)}</td><td style={{ padding: "8px 12px", borderBottom: `1px solid ${colors.border}` }}>{(b.return || 0).toFixed(1)}%</td><td style={{ padding: "8px 12px", borderBottom: `1px solid ${colors.border}` }}>{(b.vol || 0).toFixed(1)}%</td><td style={{ padding: "8px 12px", borderBottom: `1px solid ${colors.border}` }}>{b.nActive || 0}</td></tr>); })}</tbody>
                      </table>
                    </div>
                  </>) : <div style={{ padding: 40, textAlign: "center", color: colors.textDim }}>No benchmark data available</div>}
                </div>
              </div>
            )}

            {/* ─── RISK TAB ─── */}
            {activeTab === "risk" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                <div style={{ gridColumn: "1 / -1" }}><CorrelationHeatmap apiResult={apiResult} simData={data} /></div>
                <div style={{ gridColumn: "1 / -1" }}><EfficientFrontier tickers={tickers} startDate={startDate} endDate={endDate} qswResult={cs} apiResult={apiResult} /></div>
                <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
                  <SectionTitle subtitle="Historical simulation, 95% confidence" info="VaR: max daily loss at 95% confidence. CVaR (Expected Shortfall): average loss when VaR is exceeded.">Value at Risk</SectionTitle>
                  <div style={{ display: "flex", gap: 20, justifyContent: "center", padding: "20px 0" }}>
                    {[{ label: "Daily VaR", val: riskMetrics.var95, clr: colors.orange, sub: "of portfolio" }, { label: "Daily CVaR (ES)", val: riskMetrics.cvar, clr: colors.red, sub: "expected shortfall" }].map(m => (
                      <div key={m.label} style={{ textAlign: "center" }}>
                        <div style={{ fontSize: 10, color: colors.textDim, textTransform: "uppercase", marginBottom: 8 }}>{m.label}</div>
                        <div style={{ width: 120, height: 120, borderRadius: "50%", border: `4px solid ${m.clr}`, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", background: `${m.clr}10` }}>
                          <div style={{ fontSize: 28, fontWeight: 700, color: m.clr, fontFamily: "'JetBrains Mono', monospace" }}>{m.val.toFixed(2)}%</div>
                          <div style={{ fontSize: 9, color: colors.textDim }}>{m.sub}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div style={{ fontSize: 11, color: colors.textDim, textAlign: "center", marginTop: 8 }}>On a $1M portfolio: VaR = ${((riskMetrics?.var95 || 0) * 10000).toFixed(0)} | CVaR = ${((riskMetrics?.cvar || 0) * 10000).toFixed(0)} daily</div>
                </div>
                <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
                  <SectionTitle subtitle="Sector exposure from actual portfolio weights" info="Radar: portfolio vs equal-weight sector allocation. Helps spot concentration risk.">Sector Exposure</SectionTitle>
                  {sectorData?.length > 0 ? (
                    <ResponsiveContainer width="100%" height={280}>
                      <RadarChart data={sectorData.slice(0, 8).map(s => ({ factor: s.name, qsw: s.value / 100, benchmark: 1 / Math.max(sectorData.length, 1) }))}>
                        <PolarGrid stroke={colors.border} /><PolarAngleAxis dataKey="factor" tick={{ fill: colors.textMuted, fontSize: 10 }} /><PolarRadiusAxis tick={false} axisLine={false} />
                        <Radar name="Portfolio" dataKey="qsw" stroke={colors.accent} fill={colors.accent} fillOpacity={0.2} strokeWidth={2} /><Radar name="Equal Wt" dataKey="benchmark" stroke={colors.textDim} fill={colors.textDim} fillOpacity={0.05} strokeWidth={1} strokeDasharray="4 2" /><Legend wrapperStyle={{ fontSize: 11 }} />
                      </RadarChart>
                    </ResponsiveContainer>
                  ) : <div style={{ height: 280, display: "flex", alignItems: "center", justifyContent: "center", color: colors.textDim }}>No sector data available</div>}
                </div>
                <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20, gridColumn: "1 / -1" }}>
                  <SectionTitle subtitle="Sector-weighted portfolio impact under historical crisis scenarios" info="Estimated portfolio return if historical crisis happened today. Sector-specific shocks applied.">Stress Test Scenarios</SectionTitle>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginTop: 12 }}>
                    {[{ name: "2008 GFC", desc: "Lehman collapse, credit freeze" }, { name: "COVID Crash", desc: "23-day selloff, March 2020" }, { name: "2022 Rate Shock", desc: "Fed tightening, growth selloff" }, { name: "Flash Crash", desc: "Intraday chaos, May 2010" }].map(scenario => {
                      const shocks = STRESS_SECTOR_SHOCKS[scenario.name] || {};
                      let impactVal = 0;
                      if (sectorData?.length > 0) {
                        sectorData.forEach(s => { impactVal += (s.value / 100) * (shocks[s.name] || shocks.Other || -0.20) * 100; });
                      } else {
                        impactVal = (shocks["Broad Market"] || -0.30) * 100;
                      }
                      impactVal = isNaN(impactVal) ? 0 : impactVal;
                      return (
                        <div key={scenario.name} style={{ background: colors.surfaceLight, border: `1px solid ${colors.border}`, borderRadius: 8, padding: 14 }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color: colors.text, marginBottom: 4 }}>{scenario.name}</div>
                          <div style={{ fontSize: 9, color: colors.textDim, marginBottom: 10 }}>{scenario.desc}</div>
                          <div style={{ fontSize: 24, fontWeight: 700, color: impactVal >= 0 ? colors.green : colors.red, fontFamily: "'JetBrains Mono', monospace" }}>{impactVal.toFixed(1)}%</div>
                          <div style={{ fontSize: 10, color: colors.textDim }}>Est. portfolio impact</div>
                          <div style={{ marginTop: 8, height: 4, background: colors.border, borderRadius: 2, overflow: "hidden" }}><div style={{ height: "100%", width: `${Math.min(Math.abs(impactVal), 60)}%`, background: impactVal >= 0 ? colors.green : colors.red, borderRadius: 2 }} /></div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* ─── ANALYSIS TAB ─── */}
            {activeTab === "analysis" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                <div style={{ gridColumn: "1 / -1" }}>
                  <WhatIfAdjuster holdings={holdings} onWeightsChanged={handleWhatIfWeightsChanged} />
                  {whatIfMetrics && (
                    <div style={{ display: "flex", gap: 12, marginTop: 12, flexWrap: "wrap" }}>
                      <MetricCard label="What-If Sharpe" value={whatIfMetrics.sharpe.toFixed(3)} color={whatIfMetrics.sharpe > (qsw?.sharpe || 0) ? colors.green : colors.orange} description="Adjusted portfolio" info="Sharpe if you apply the adjusted weights." />
                      <MetricCard label="What-If Return" value={(whatIfMetrics.portReturn * 100).toFixed(1)} unit="%" color={colors.accent} description="Annualized" info="Expected return with adjusted weights." />
                      <MetricCard label="What-If Vol" value={(whatIfMetrics.portVol * 100).toFixed(1)} unit="%" color={colors.orange} description="Annualized" info="Volatility with adjusted weights." />
                      <MetricCard label="Active Positions" value={whatIfMetrics.nActive} color={colors.purple} description="Above 0.5% weight" info="Count of positions above 0.5% after adjustment." />
                    </div>
                  )}
                </div>
                <div style={{ gridColumn: "1 / -1" }}><RegimeComparison tickers={tickers} startDate={startDate} endDate={endDate} objective={objective} strategyPreset="balanced" constraints={constraints} apiResult={apiResult} /></div>
              </div>
            )}

            {/* ─── SENSITIVITY TAB ─── */}
            {activeTab === "sensitivity" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                {dataSource === "api" && (
                  <div style={{ gridColumn: "1 / -1", display: "flex", gap: 8, alignItems: "center" }}>
                    <button onClick={async () => {
                      setSensitivityLoading(true);
                      try {
                        const basePayload = { tickers, startDate, endDate, regime, evolutionTime, turnoverLimit, objective, strategyPreset: "balanced", constraints };
                        const omegaReqs = [0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60].map(o => ({ ...basePayload, omega: o, maxWeight }));
                        const mwReqs = [0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30].map(mw => ({ ...basePayload, omega, maxWeight: mw }));
                        const [omegaResp, mwResp] = await Promise.all([optimizeBatch(omegaReqs), optimizeBatch(mwReqs)]);
                        const omegaPts = (omegaResp.results || []).filter(r => r.status === "ok").map((r, i) => ({ omega: omegaReqs[i].omega.toFixed(2), sharpe: r.result?.qsw_result?.sharpe_ratio || 0, return: (r.result?.qsw_result?.expected_return || 0) * 100, vol: (r.result?.qsw_result?.volatility || 0) * 100, nActive: r.result?.qsw_result?.n_active || 0 }));
                        const mwPts = (mwResp.results || []).filter(r => r.status === "ok").map((r, i) => ({ maxWeight: mwReqs[i].maxWeight.toFixed(2), sharpe: r.result?.qsw_result?.sharpe_ratio || 0, return: (r.result?.qsw_result?.expected_return || 0) * 100, vol: (r.result?.qsw_result?.volatility || 0) * 100, nActive: r.result?.qsw_result?.n_active || 0 }));
                        setSensitivityData({ omega: omegaPts, maxWeight: mwPts });
                        toast.success("Sensitivity sweep complete");
                      } catch (err) { toast.error(`Sensitivity sweep failed: ${err.message}`); } finally { setSensitivityLoading(false); }
                    }} disabled={sensitivityLoading} style={{ padding: "8px 16px", backgroundColor: colors.accent, color: "white", border: "none", borderRadius: 6, cursor: sensitivityLoading ? "not-allowed" : "pointer", fontSize: 12, fontFamily: "'JetBrains Mono', monospace", opacity: sensitivityLoading ? 0.6 : 1 }}>
                      {sensitivityLoading ? "Running Sweep..." : "Run API Sensitivity Sweep"}
                    </button>
                    <span style={{ fontSize: 10, color: colors.textDim }}>Sweeps omega and max-weight via batch optimize</span>
                  </div>
                )}
                <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
                  <SectionTitle subtitle="Sharpe ratio as omega varies" info="Shows how Sharpe changes as omega varies. Helps tune the quantum-classical coupling.">{dataSource === "api" ? "Omega Sensitivity (API)" : "Omega Sensitivity"}</SectionTitle>
                  {(() => {
                    const pts = dataSource === "api" ? (sensitivityData?.omega || []) : omegaSensitivity;
                    return pts?.length > 0 ? (
                      <ResponsiveContainer width="100%" height={280}><AreaChart data={pts}><defs><linearGradient id="omegaGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={colors.accent} stopOpacity={0.3} /><stop offset="100%" stopColor={colors.accent} stopOpacity={0} /></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke={colors.border} /><XAxis dataKey="omega" stroke={colors.textDim} tick={{ fontSize: 10 }} /><YAxis stroke={colors.textDim} tick={{ fontSize: 10 }} /><Tooltip content={<CustomTooltip />} />{typeof omega === "number" && <ReferenceLine x={omega.toFixed(2)} stroke={colors.accent} strokeDasharray="3 3" label={{ value: "Current", fill: colors.accent, fontSize: 10 }} />}<Area type="monotone" dataKey="sharpe" stroke={colors.accent} fill="url(#omegaGrad)" strokeWidth={2} name="Sharpe" /></AreaChart></ResponsiveContainer>
                    ) : <div style={{ height: 280, display: "flex", alignItems: "center", justifyContent: "center", color: colors.textDim }}>{dataSource === "api" ? "Click 'Run API Sensitivity Sweep' above" : "No sensitivity data available"}</div>;
                  })()}
                </div>
                <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
                  <SectionTitle subtitle={dataSource === "api" ? "Sharpe vs. max weight constraint" : "Effect of evolution time on Sharpe"} info={dataSource === "api" ? "How max weight per position affects Sharpe." : "How evolution time (diffusion steps) affects Sharpe and concentration."}>
                    {dataSource === "api" ? "Max Weight Sensitivity (API)" : "Evolution Time Sensitivity"}
                  </SectionTitle>
                  {(() => {
                    if (dataSource === "api") {
                      const pts = sensitivityData?.maxWeight || [];
                      return pts.length > 0 ? (
                        <ResponsiveContainer width="100%" height={280}><AreaChart data={pts}><defs><linearGradient id="mwGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={colors.green} stopOpacity={0.3} /><stop offset="100%" stopColor={colors.green} stopOpacity={0} /></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke={colors.border} /><XAxis dataKey="maxWeight" stroke={colors.textDim} tick={{ fontSize: 10 }} /><YAxis stroke={colors.textDim} tick={{ fontSize: 10 }} /><Tooltip content={<CustomTooltip />} />{typeof maxWeight === "number" && <ReferenceLine x={maxWeight.toFixed(2)} stroke={colors.green} strokeDasharray="3 3" label={{ value: "Current", fill: colors.green, fontSize: 10 }} />}<Area type="monotone" dataKey="sharpe" stroke={colors.green} fill="url(#mwGrad)" strokeWidth={2} name="Sharpe" /></AreaChart></ResponsiveContainer>
                      ) : <div style={{ height: 280, display: "flex", alignItems: "center", justifyContent: "center", color: colors.textDim }}>Click 'Run API Sensitivity Sweep' above</div>;
                    }
                    return evolSensitivity?.length > 0 ? (
                      <ResponsiveContainer width="100%" height={280}><LineChart data={evolSensitivity}><CartesianGrid strokeDasharray="3 3" stroke={colors.border} /><XAxis dataKey="time" stroke={colors.textDim} tick={{ fontSize: 10 }} label={{ value: "Evolution Time (t)", position: "bottom", fill: colors.textDim, fontSize: 11 }} /><YAxis yAxisId="left" stroke={colors.textDim} tick={{ fontSize: 10 }} /><YAxis yAxisId="right" orientation="right" stroke={colors.textDim} tick={{ fontSize: 10 }} /><Tooltip content={<CustomTooltip />} /><Legend wrapperStyle={{ fontSize: 11 }} />{typeof evolutionTime === "number" && <ReferenceLine x={evolutionTime} yAxisId="left" stroke={colors.accent} strokeDasharray="3 3" />}<Line yAxisId="left" type="monotone" dataKey="sharpe" stroke={colors.accent} strokeWidth={2} dot={false} name="Sharpe" /><Line yAxisId="right" type="monotone" dataKey="nActive" stroke={colors.purple} strokeWidth={2} dot={false} name="Active Positions" /></LineChart></ResponsiveContainer>
                    ) : <div style={{ height: 280, display: "flex", alignItems: "center", justifyContent: "center", color: colors.textDim }}>No sensitivity data available</div>;
                  })()}
                </div>
                <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20, gridColumn: "1 / -1" }}>
                  <SectionTitle subtitle="Pairwise correlation between top holdings" info="Correlation of current holdings. Green = diversification; red = concentration risk.">Correlation Matrix</SectionTitle>
                  {corrData?.length > 0 ? (
                    <div style={{ overflowX: "auto" }}>
                      <table style={{ borderCollapse: "collapse", margin: "0 auto" }}>
                        <thead><tr><th style={{ padding: 6, fontSize: 10, color: colors.textDim }}></th>{corrData.map((r, idx) => <th key={r?.name || idx} style={{ padding: 6, fontSize: 10, color: colors.textMuted, fontFamily: "'JetBrains Mono', monospace", transform: "rotate(-45deg)", height: 50 }}>{r?.name || "?"}</th>)}</tr></thead>
                        <tbody>{corrData.map((row, ri) => (<tr key={row?.name || ri}><td style={{ padding: "4px 8px", fontSize: 10, color: colors.textMuted, fontFamily: "'JetBrains Mono', monospace", textAlign: "right" }}>{row?.name}</td>{corrData.map((col, ci) => { const val = typeof row[col?.name] === "number" ? row[col.name] : 0; const absVal = Math.abs(val); const bg = ri === ci ? colors.accent + "30" : val > 0 ? `rgba(239,68,68,${absVal * 0.6})` : `rgba(16,185,129,${absVal * 0.6})`; return <td key={ci} style={{ padding: 4, textAlign: "center", fontSize: 10, color: colors.text, background: bg, fontFamily: "'JetBrains Mono', monospace", width: 44, height: 32, borderRadius: 2, border: `1px solid ${colors.bg}` }}>{val.toFixed(2)}</td>; })}</tr>))}</tbody>
                      </table>
                      <div style={{ display: "flex", justifyContent: "center", gap: 16, marginTop: 12, fontSize: 10, color: colors.textDim }}>
                        <span><span style={{ display: "inline-block", width: 12, height: 12, background: "rgba(16,185,129,0.5)", borderRadius: 2, verticalAlign: "middle", marginRight: 4 }}></span>Negative (diversification)</span>
                        <span><span style={{ display: "inline-block", width: 12, height: 12, background: "rgba(239,68,68,0.5)", borderRadius: 2, verticalAlign: "middle", marginRight: 4 }}></span>Positive (concentration)</span>
                      </div>
                    </div>
                  ) : <div style={{ padding: 40, textAlign: "center", color: colors.textDim }}>{dataSource === "api" ? "Run an optimization first to see the correlation matrix" : "No correlation data available"}</div>}
                </div>
                <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20, gridColumn: "1 / -1" }}>
                  <SectionTitle subtitle="How omega affects return, risk, and concentration" info="Bar chart showing return, volatility, and active positions at each omega value.">Omega Impact Breakdown</SectionTitle>
                  {(() => {
                    const pts = dataSource === "api" ? (sensitivityData?.omega || []) : omegaSensitivity;
                    return pts?.length > 0 ? (
                      <ResponsiveContainer width="100%" height={280}><BarChart data={pts.filter((_, i) => dataSource === "api" || i % 2 === 0)}><CartesianGrid strokeDasharray="3 3" stroke={colors.border} /><XAxis dataKey="omega" stroke={colors.textDim} tick={{ fontSize: 10 }} /><YAxis stroke={colors.textDim} tick={{ fontSize: 10 }} /><Tooltip content={<CustomTooltip />} /><Legend wrapperStyle={{ fontSize: 11 }} /><Bar dataKey="return" name="Return (%)" fill={colors.green} radius={[2, 2, 0, 0]} /><Bar dataKey="vol" name="Volatility (%)" fill={colors.orange} radius={[2, 2, 0, 0]} /><Bar dataKey="nActive" name="Positions" fill={colors.purple} radius={[2, 2, 0, 0]} /></BarChart></ResponsiveContainer>
                    ) : <div style={{ height: 280, display: "flex", alignItems: "center", justifyContent: "center", color: colors.textDim }}>{dataSource === "api" ? "Run sensitivity sweep first" : "No sensitivity data available"}</div>;
                  })()}
                </div>
              </div>
            )}

            {/* ─── SCENARIOS TAB ─── */}
            {activeTab === "scenarios" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 20 }}>
                <ScenarioTester objective={objective} constraints={constraints} strategyPreset="balanced" omega={omega} evolutionTime={evolutionTime} regime={regime} onLoadScenario={({ tickers: t, startDate: sd, endDate: ed, backtestResult: bt }) => { setTickers(t); setStartDate(sd); setEndDate(ed); setBacktestResult(bt); setMetricsView("backtest"); setActiveTab("performance"); toast.info("Scenario loaded"); }} />
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardThemeContext.Provider>
  );
}
