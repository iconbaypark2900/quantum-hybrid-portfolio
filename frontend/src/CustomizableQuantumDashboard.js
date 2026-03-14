import React, { useState, useMemo, useEffect, createContext, useContext } from "react";
import { FaCaretUp, FaCaretDown, FaCheck, FaEdit, FaBriefcase, FaChartLine, FaShieldAlt, FaSlidersH, FaCircle, FaRegCircle, FaAdjust, FaBolt, FaDotCircle, FaUndo, FaStar } from "react-icons/fa";
import { getObjectives, optimizePortfolio, fetchMarketData } from "./services/api";
import { LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter, ReferenceLine } from "recharts";

const DashboardThemeContext = createContext(null);
function useDashboardTheme() { return useContext(DashboardThemeContext) || colors; }

// ─── SEEDED RANDOM ───
let seed = 42;
function seededRandom() {
  seed = (seed * 16807 + 0) % 2147483647;
  return (seed - 1) / 2147483646;
}
function resetSeed(s = 42) { seed = s; }

// Default ticker and sector lists (used when no custom list provided)
const DEFAULT_TICKERS = ["AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","JPM","V","JNJ","PG","UNH","HD","MA","BAC","DIS","NFLX","KO","PFE","CVX","WMT","MRK","ABT","ADBE","NKE","PEP","T","VZ","PYPL","BRK"];
const DEFAULT_SECTORS = ["Tech","Tech","Tech","Tech","Tech","Tech","Tech","Finance","Finance","Health","Consumer","Health","Consumer","Finance","Finance","Consumer","Tech","Consumer","Health","Energy","Consumer","Health","Health","Tech","Consumer","Consumer","Telecom","Telecom","Tech","Finance"];

// ─── SIMULATION ENGINE ───
function generateMarketData(nAssets, nDays, regime, seedVal, customTickerList) {
  resetSeed(seedVal);
  const regimeParams = {
    bull: { drift: 0.0008, vol: 0.012, corrBase: 0.3 },
    bear: { drift: -0.0003, vol: 0.022, corrBase: 0.6 },
    volatile: { drift: 0.0002, vol: 0.028, corrBase: 0.45 },
    normal: { drift: 0.0004, vol: 0.015, corrBase: 0.35 },
  };
  const { drift, vol, corrBase } = regimeParams[regime];
  const rawNames = (Array.isArray(customTickerList) && customTickerList.length > 0) ? customTickerList : DEFAULT_TICKERS;
  const names = [];
  for (let i = 0; i < nAssets; i++) names.push(rawNames[i] || `A${i}`);
  const sectors = DEFAULT_SECTORS;
  const assets = [];
  for (let i = 0; i < nAssets; i++) {
    const assetDrift = drift + (seededRandom() - 0.4) * 0.001;
    const assetVol = vol * (0.7 + seededRandom() * 0.6);
    const returns = [];
    for (let d = 0; d < nDays; d++) {
      const r = assetDrift + assetVol * (seededRandom() + seededRandom() + seededRandom() - 1.5) * 0.816;
      returns.push(r);
    }
    const annReturn = returns.reduce((a, b) => a + b, 0) / nDays * 252;
    const annVol = Math.sqrt(returns.map(r => r * r).reduce((a, b) => a + b, 0) / nDays) * Math.sqrt(252);
    assets.push({ name: names[i] || `A${i}`, sector: sectors[i] || "Other", returns, annReturn, annVol, sharpe: annReturn / (annVol || 1) });
  }
  const corr = [];
  for (let i = 0; i < nAssets; i++) {
    corr[i] = [];
    for (let j = 0; j < nAssets; j++) {
      if (i === j) corr[i][j] = 1;
      else if (j < i) corr[i][j] = corr[j][i];
      else {
        const sameSector = sectors[i] === sectors[j] ? 0.2 : 0;
        corr[i][j] = Math.max(-0.3, Math.min(0.95, corrBase + sameSector + (seededRandom() - 0.5) * 0.4));
      }
    }
  }
  return { assets, corr, regime };
}

function runQSWOptimization(data, omega, evolutionTime, maxWeight, turnoverLimit, evolutionMethod = 'continuous') {
  const n = data.assets.length;
  const weights = new Array(n).fill(0);
  const sharpes = data.assets.map(a => Math.max(0.01, a.sharpe + 0.5));
  const totalSharpe = sharpes.reduce((a, b) => a + b, 0);

  // Simulate quantum walk: Sharpe-weighted potential with correlation coupling
  for (let i = 0; i < n; i++) {
    let potential = sharpes[i] / totalSharpe;
    let coupling = 0;
    for (let j = 0; j < n; j++) {
      if (i !== j) {
        const diversBenefit = (1 - Math.abs(data.corr[i][j])) * sharpes[j] / totalSharpe;
        coupling += diversBenefit;
      }
    }
    weights[i] = (1 - omega) * potential + omega * coupling / (n - 1);
  }

  // Apply different evolution methods
  switch(evolutionMethod) {
    case 'discrete':
      // Discrete-time quantum walk simulation
      const dtSteps = evolutionTime * 2; // More steps for discrete
      for (let step = 0; step < dtSteps; step++) {
        const newWeights = [...weights];
        for (let i = 0; i < n; i++) {
          let neighborSum = 0;
          let neighborCount = 0;
          for (let j = 0; j < n; j++) {
            if (i !== j && Math.abs(data.corr[i][j]) > 0.1) {
              neighborSum += weights[j];
              neighborCount++;
            }
          }
          if (neighborCount > 0) {
            newWeights[i] = (weights[i] + neighborSum / neighborCount) / 2;
          }
        }
        for (let i = 0; i < n; i++) {
          weights[i] = newWeights[i];
        }
      }
      break;
      
    case 'decoherent':
      // Apply decoherence effect
      const decoherenceRate = 0.15; // Default decoherence rate
      for (let i = 0; i < n; i++) {
        weights[i] = (1 - decoherenceRate) * weights[i] + decoherenceRate * (1/n);
      }
      break;
      
    default: // continuous
      // Evolution smoothing
      const smoothFactor = Math.exp(-evolutionTime / 50);
      const equalW = 1 / n;
      for (let i = 0; i < n; i++) {
        weights[i] = weights[i] * (1 - smoothFactor) + equalW * smoothFactor;
      }
  }

  // Constraints
  for (let i = 0; i < n; i++) weights[i] = Math.min(weights[i], maxWeight);
  for (let i = 0; i < n; i++) if (weights[i] < 0.005) weights[i] = 0;
  const sum = weights.reduce((a, b) => a + b, 0);
  if (sum === 0) {
    for (let i = 0; i < n; i++) weights[i] = 1 / n;
  } else {
    for (let i = 0; i < n; i++) weights[i] /= sum;
  }

  // Portfolio metrics
  let portReturn = 0, portVar = 0;
  for (let i = 0; i < n; i++) {
    portReturn += weights[i] * data.assets[i].annReturn;
    for (let j = 0; j < n; j++) {
      portVar += weights[i] * weights[j] * data.corr[i][j] * data.assets[i].annVol * data.assets[j].annVol;
    }
  }
  const portVol = Math.sqrt(Math.max(0, portVar));
  const sharpe = portReturn / (portVol || 1);
  return { weights, portReturn, portVol, sharpe, nActive: weights.filter(w => w > 0.005).length };
}

function runQuantumAnnealingOptimization(data, maxWeight) {
  // Simulate quantum annealing optimization
  const n = data.assets.length;
  const weights = new Array(n).fill(0);
  
  // Initialize with random weights that sum to 1
  for (let i = 0; i < n; i++) {
    weights[i] = seededRandom();
  }
  const sum = weights.reduce((a, b) => a + b, 0);
  for (let i = 0; i < n; i++) {
    weights[i] /= sum;
  }
  
  // Simulate annealing process
  const iterations = 100;
  let currentSharpe = calculateSharpe(weights, data);
  
  for (let iter = 0; iter < iterations; iter++) {
    // Generate neighbor solution with quantum fluctuations
    const neighborWeights = [...weights];
    const temp = 100 * Math.exp(-iter / 20); // Cooling schedule
    
    for (let i = 0; i < n; i++) {
      // Add quantum-inspired perturbation
      const quantumPerturbation = (seededRandom() - 0.5) * 0.1;
      neighborWeights[i] += quantumPerturbation;
      neighborWeights[i] = Math.max(0, Math.min(maxWeight, neighborWeights[i]));
    }
    
    // Renormalize
    const neighborSum = neighborWeights.reduce((a, b) => a + b, 0);
    for (let i = 0; i < n; i++) {
      neighborWeights[i] /= neighborSum;
    }
    
    const neighborSharpe = calculateSharpe(neighborWeights, data);
    
    // Accept or reject based on Metropolis criterion
    if (neighborSharpe > currentSharpe || Math.exp(-(currentSharpe - neighborSharpe) / temp) > seededRandom()) {
      for (let i = 0; i < n; i++) {
        weights[i] = neighborWeights[i];
      }
      currentSharpe = neighborSharpe;
    }
  }
  
  // Apply constraints
  for (let i = 0; i < n; i++) weights[i] = Math.min(weights[i], maxWeight);
  for (let i = 0; i < n; i++) if (weights[i] < 0.005) weights[i] = 0;
  const finalSum = weights.reduce((a, b) => a + b, 0);
  if (finalSum > 0) {
    for (let i = 0; i < n; i++) weights[i] /= finalSum;
  }
  
  let portReturn = 0, portVar = 0;
  for (let i = 0; i < n; i++) {
    portReturn += weights[i] * data.assets[i].annReturn;
    for (let j = 0; j < n; j++) {
      portVar += weights[i] * weights[j] * data.corr[i][j] * data.assets[i].annVol * data.assets[j].annVol;
    }
  }
  const portVol = Math.sqrt(Math.max(0, portVar));
  const sharpe = portReturn / (portVol || 1);
  return { weights, portReturn, portVol, sharpe, nActive: weights.filter(w => w > 0.005).length };
}

function calculateSharpe(weights, data) {
  const n = data.assets.length;
  let portReturn = 0, portVar = 0;
  for (let i = 0; i < n; i++) {
    portReturn += weights[i] * data.assets[i].annReturn;
    for (let j = 0; j < n; j++) {
      portVar += weights[i] * weights[j] * data.corr[i][j] * data.assets[i].annVol * data.assets[j].annVol;
    }
  }
  const portVol = Math.sqrt(Math.max(0, portVar));
  return portReturn / (portVol || 1);
}

function runBenchmarks(data) {
  const n = data.assets.length;
  const calc = (w) => {
    let r = 0, v = 0;
    for (let i = 0; i < n; i++) { r += w[i] * data.assets[i].annReturn; for (let j = 0; j < n; j++) v += w[i] * w[j] * data.corr[i][j] * data.assets[i].annVol * data.assets[j].annVol; }
    const vol = Math.sqrt(Math.max(0, v));
    return { weights: w, portReturn: r, portVol: vol, sharpe: r / (vol || 1) };
  };

  // Equal weight
  const ew = new Array(n).fill(1 / n);

  // Min variance (approximate: inverse volatility)
  const invVol = data.assets.map(a => 1 / (a.annVol || 1));
  const ivSum = invVol.reduce((a, b) => a + b, 0);
  const mv = invVol.map(v => v / ivSum);

  // Risk parity (approximate: inverse vol weighted)
  const riskBudget = data.assets.map(a => 1 / (a.annVol * a.annVol || 1));
  const rbSum = riskBudget.reduce((a, b) => a + b, 0);
  const rp = riskBudget.map(v => v / rbSum);

  // Max Sharpe (approximate: Sharpe-weighted)
  const sharpeW = data.assets.map(a => Math.max(0, a.sharpe));
  const swSum = sharpeW.reduce((a, b) => a + b, 0) || 1;
  const ms = sharpeW.map(v => v / swSum);

  return {
    equalWeight: { name: "Equal Weight", ...calc(ew) },
    minVariance: { name: "Min Variance", ...calc(mv) },
    riskParity: { name: "Risk Parity", ...calc(rp) },
    maxSharpe: { name: "Max Sharpe", ...calc(ms) }
  };
}

function simulateEquityCurve(data, weights, nDays) {
  const curve = [{ day: 0, value: 100 }];
  let val = 100;
  for (let d = 0; d < Math.min(nDays, data.assets[0]?.returns.length || 0); d++) {
    let dayReturn = 0;
    for (let i = 0; i < weights.length; i++) {
      dayReturn += weights[i] * (data.assets[i]?.returns[d] || 0);
    }
    val *= (1 + dayReturn);
    if (d % 5 === 0) curve.push({ day: d + 1, value: val });
  }
  return curve;
}

function computeVaR(data, weights, confidence) {
  const n = weights.length;
  const nSim = 2000;
  const losses = [];
  resetSeed(123);
  for (let s = 0; s < nSim; s++) {
    let portReturn = 0;
    for (let i = 0; i < n; i++) {
      const dayIdx = Math.floor(seededRandom() * (data.assets[i]?.returns.length || 1));
      portReturn += weights[i] * (data.assets[i]?.returns[dayIdx] || 0);
    }
    losses.push(-portReturn);
  }
  losses.sort((a, b) => a - b);
  const varIdx = Math.floor(nSim * confidence);
  const var95 = losses[varIdx] || 0;
  const cvar = losses.slice(varIdx).reduce((a, b) => a + b, 0) / (nSim - varIdx || 1);
  return { var95: var95 * 100, cvar: cvar * 100 };
}

// ─── ACCESSIBILITY-FRIENDLY STYLES ───
const colors = {
  bg: "#0A0E1A",
  surface: "#111827",
  surfaceLight: "#1A2235",
  border: "#1E293B",
  borderLight: "#2D3A52",
  text: "#E2E8F0",
  textMuted: "#8B9DC3",
  textDim: "#4A5578",
  accent: "#3B82F6",
  accentGlow: "rgba(59,130,246,0.15)",
  green: "#10B981",
  greenDim: "rgba(16,185,129,0.15)",
  red: "#EF4444",
  redDim: "rgba(239,68,68,0.15)",
  orange: "#F59E0B",
  purple: "#8B5CF6",
  cyan: "#06B6D4",
  pink: "#EC4899",
  // High contrast colors for accessibility
  highContrastText: "#FFFFFF",
  highContrastBg: "#000000",
  focusOutline: "#FFD700", // Gold for focus indicators
  focusOutlineWidth: "3px"
};

const chartColors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4", "#EC4899", "#F97316"];
const benchmarkColors = { 
  "QSW": "#3B82F6", 
  "QSW-Discrete": "#8B5CF6", 
  "QSW-Decoherent": "#06B6D4", 
  "Quantum Annealing": "#EC4899",
  "Equal Weight": "#8B9DC3", 
  "Min Variance": "#10B981", 
  "Risk Parity": "#F59E0B", 
  "Max Sharpe": "#8B5CF6" 
};

// ─── CUSTOMIZABLE COMPONENTS ───

function CustomizableSlider({ label, value, onChange, min, max, step, unit = "", info, customLabel, customColor }) {
  const id = `slider-${label.replace(/\s+/g, '-').toLowerCase()}`;
  
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <label htmlFor={id} style={{ fontSize: 12, color: customColor || colors.textMuted, letterSpacing: "0.05em", textTransform: "uppercase", fontFamily: "'JetBrains Mono', monospace", cursor: "pointer" }}>
          {customLabel || label}
        </label>
        <span style={{ fontSize: 13, color: customColor || colors.accent, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>
          {typeof value === 'number' ? value.toFixed(step < 1 ? 2 : 0) : value}{unit}
        </span>
      </div>
      <input 
        id={id}
        type="range" 
        min={min} 
        max={max} 
        step={step} 
        value={value} 
        onChange={e => onChange(parseFloat(e.target.value))}
        aria-label={customLabel || label}
        aria-valuenow={value}
        aria-valuemin={min}
        aria-valuemax={max}
        style={{ 
          width: "100%", 
          height: 8, 
          appearance: "none", 
          background: `linear-gradient(to right, ${customColor || colors.accent} ${((value - min) / (max - min)) * 100}%, ${colors.border} ${((value - min) / (max - min)) * 100}%)`, 
          borderRadius: 4, 
          outline: "none", 
          cursor: "pointer",
          marginTop: 8
        }} 
        onFocus={(e) => {
          e.target.style.boxShadow = `0 0 0 ${colors.focusOutlineWidth} ${colors.focusOutline}`;
        }}
        onBlur={(e) => {
          e.target.style.boxShadow = "none";
        }}
      />
      {info && <div style={{ fontSize: 10, color: colors.textDim, marginTop: 4, fontStyle: "italic" }}>{info}</div>}
    </div>
  );
}

function DraggableMetricCard({ label, value, unit, delta, description, color, onDrag, onDrop, draggable = true }) {
  const theme = useDashboardTheme();
  const accentColor = color || theme.accent;
  return (
    <div 
      role="region"
      aria-label={`Metric card: ${label}`}
      draggable={draggable}
      onDragStart={onDrag}
      onDragOver={(e) => e.preventDefault()}
      onDrop={onDrop}
      style={{ 
        background: theme.surface, 
        border: `1px solid ${theme.border}`, 
        borderRadius: 8, 
        padding: "14px 16px", 
        flex: 1, 
        minWidth: 140,
        cursor: draggable ? 'move' : 'default',
        transition: 'transform 0.2s, box-shadow 0.2s',
        outline: 'none'
      }}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          if (onDrag) {
            const fakeEvent = { target: e.currentTarget };
            onDrag(fakeEvent);
          }
        }
      }}
      onFocus={(e) => {
        e.currentTarget.style.boxShadow = `0 0 0 ${theme.focusOutlineWidth || "3px"} ${theme.focusOutline || theme.accent}`;
      }}
      onBlur={(e) => {
        e.currentTarget.style.boxShadow = 'none';
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-2px)';
        e.currentTarget.style.boxShadow = `0 4px 12px rgba(0,0,0,0.15)`;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      <div style={{ fontSize: 11, color: theme.textDim, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>{label}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
        <span style={{ fontSize: 24, fontWeight: 700, color: accentColor, fontFamily: "'JetBrains Mono', monospace" }}>{value}</span>
        {unit && <span style={{ fontSize: 12, color: theme.textMuted }}>{unit}</span>}
      </div>
      {delta !== undefined && (
        <div style={{ fontSize: 11, color: delta >= 0 ? theme.green : theme.red, marginTop: 4, fontFamily: "'JetBrains Mono', monospace" }}>
          {delta >= 0 ? <FaCaretUp size={10} style={{ display: "inline", verticalAlign: "middle" }} /> : <FaCaretDown size={10} style={{ display: "inline", verticalAlign: "middle" }} />} {Math.abs(delta).toFixed(1)}% vs benchmark
        </div>
      )}
      {description && <div style={{ fontSize: 10, color: theme.textDim, marginTop: 4 }}>{description}</div>}
    </div>
  );
}

function CustomizableTabButton({ active, onClick, children, icon, customStyle, theme }) {
  const t = theme || colors;
  return (
    <button 
      role="tab"
      aria-selected={active}
      onClick={onClick} 
      style={{
        padding: "10px 18px", 
        background: active ? (t.accentGlow || "rgba(59,130,246,0.15)") : "transparent",
        border: `1px solid ${active ? t.accent : "transparent"}`, 
        borderRadius: 6,
        color: active ? t.accent : (t.textMuted || t.text), 
        fontSize: 14, 
        fontWeight: active ? 600 : 500,
        cursor: "pointer", 
        transition: "all 0.2s", 
        display: "flex", 
        alignItems: "center", 
        gap: 6,
        fontFamily: "'JetBrains Mono', 'Consolas', monospace", 
        letterSpacing: "0.02em",
        outline: 'none',
        ...(customStyle || {})
      }}
      onFocus={(e) => {
        e.target.style.boxShadow = `0 0 0 ${t.focusOutlineWidth || "3px"} ${t.focusOutline || "#3B82F6"}`;
      }}
      onBlur={(e) => {
        e.target.style.boxShadow = 'none';
      }}
    >
      {icon && <span style={{ fontSize: 15 }}>{icon}</span>}
      {children}
    </button>
  );
}

function InteractiveSectionTitle({ children, subtitle, onEdit, editable = false }) {
  const theme = useDashboardTheme();
  const [isEditing, setIsEditing] = useState(false);
  const [titleText, setTitleText] = useState(children);

  const handleEdit = () => {
    if (editable) setIsEditing(true);
  };

  const handleSave = () => {
    setIsEditing(false);
    if (onEdit) onEdit(titleText);
  };

  return (
    <div style={{ marginBottom: 16 }}>
      {isEditing ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input
            type="text"
            value={titleText}
            onChange={(e) => setTitleText(e.target.value)}
            style={{
              fontSize: 15,
              fontWeight: 700,
              margin: 0,
              padding: '4px 8px',
              borderRadius: 4,
              border: `1px solid ${theme.accent}`,
              fontFamily: "'Space Grotesk', sans-serif",
              letterSpacing: "-0.01em",
              backgroundColor: theme.surface,
              color: theme.text,
              outline: 'none'
            }}
            autoFocus
            onBlur={handleSave}
            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
          />
          <button 
            onClick={handleSave}
            style={{
              padding: '4px 8px',
              backgroundColor: theme.accent,
              color: theme.bg,
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontWeight: 600
            }}
          >
            <FaCheck size={14} />
          </button>
        </div>
      ) : (
        <div 
          onClick={handleEdit}
          style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: editable ? 'pointer' : 'default' }}
        >
          <h3 style={{ fontSize: 15, fontWeight: 700, color: theme.text, margin: 0, fontFamily: "'Space Grotesk', sans-serif", letterSpacing: "-0.01em" }}>
            {titleText}
          </h3>
          {editable && <span style={{ fontSize: 12, color: theme.textMuted }}><FaEdit size={12} /></span>}
        </div>
      )}
      {subtitle && <p style={{ fontSize: 11, color: theme.textDim, margin: "4px 0 0 0" }}>{subtitle}</p>}
    </div>
  );
}

function PresetSelector({ presets, onSelect, currentPreset }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 12, color: colors.textMuted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>
        PRESETS
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {presets.map((preset, index) => (
          <button
            key={index}
            onClick={() => onSelect(preset)}
            style={{
              padding: "6px 12px",
              background: currentPreset?.name === preset.name ? colors.accentGlow : colors.surface,
              border: `1px solid ${currentPreset?.name === preset.name ? colors.accent : colors.border}`,
              borderRadius: 4,
              color: currentPreset?.name === preset.name ? colors.accent : colors.textMuted,
              fontSize: 11,
              cursor: "pointer",
              fontFamily: "'JetBrains Mono', monospace",
              transition: "all 0.2s"
            }}
          >
            {preset.name}
          </button>
        ))}
      </div>
    </div>
  );
}

function ThemeSelector({ themes, onSelect, currentTheme }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 12, color: colors.textMuted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>
        THEME
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        {themes.map((theme, index) => (
          <button
            key={index}
            onClick={() => onSelect(theme)}
            style={{
              width: 30,
              height: 30,
              borderRadius: "50%",
              background: theme.accent,
              border: `2px solid ${currentTheme?.accent === theme.accent ? colors.accent : "transparent"}`,
              cursor: "pointer",
              transition: "all 0.2s"
            }}
          />
        ))}
      </div>
    </div>
  );
}

function ExportControls({ onExport, exportFormats = ['png', 'svg', 'csv'] }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 12, color: colors.textMuted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>
        EXPORT OPTIONS
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {exportFormats.map(format => (
          <button
            key={format}
            onClick={() => onExport(format)}
            style={{
              padding: "6px 12px",
              background: colors.surface,
              border: `1px solid ${colors.border}`,
              borderRadius: 4,
              color: colors.text,
              fontSize: 11,
              cursor: "pointer",
              fontFamily: "'JetBrains Mono', monospace",
              transition: "all 0.2s"
            }}
            onMouseEnter={(e) => e.target.style.background = colors.surfaceLight}
            onMouseLeave={(e) => e.target.style.background = colors.surface}
          >
            {format.toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── MAIN DASHBOARD ───
export default function QuantumPortfolioDashboard() {
  // Parameters
  const [nAssets, setNAssets] = useState(20);
  const [regime, setRegime] = useState("normal");
  const [omega, setOmega] = useState(0.30);
  const [evolutionTime, setEvolutionTime] = useState(10);
  const [maxWeight, setMaxWeight] = useState(0.10);
  const [turnoverLimit, setTurnoverLimit] = useState(0.20);
  const [dataSeed, setDataSeed] = useState(42);
  const [activeTab, setActiveTab] = useState("portfolio");
  const [evolutionMethod, setEvolutionMethod] = useState("continuous");
  const [dashboardTitle, setDashboardTitle] = useState("Quantum Portfolio Lab");
  const [dashboardSubtitle, setDashboardSubtitle] = useState("QSW-Inspired Optimization Explorer");
  const [activeTheme, setActiveTheme] = useState(colors);
  const [savedPresets, setSavedPresets] = useState([
    { name: "Conservative", nAssets: 10, omega: 0.25, evolutionTime: 15, maxWeight: 0.15, regime: "normal" },
    { name: "Aggressive", nAssets: 30, omega: 0.45, evolutionTime: 5, maxWeight: 0.08, regime: "bull" },
    { name: "Balanced", nAssets: 20, omega: 0.30, evolutionTime: 10, maxWeight: 0.10, regime: "normal" }
  ]);
  const [customPresets, setCustomPresets] = useState([]);
  const [isDragging, setIsDragging] = useState(null);
  // Custom tickers: comma-separated string, e.g. "AAPL, MSFT, GOOGL"
  const [customTickersString, setCustomTickersString] = useState("");
  // Which strategies/benchmarks to show (all enabled by default)
  const [selectedStrategies, setSelectedStrategies] = useState(new Set([
    "QSW", "Equal Weight", "Min Variance", "Risk Parity", "Max Sharpe",
    "QSW-Discrete", "QSW-Decoherent", "Quantum Annealing"
  ]));
  // Live API (backend optimization including QAOA on IBM Quantum)
  const [apiObjectives, setApiObjectives] = useState([]);
  const [apiObjective, setApiObjective] = useState("max_sharpe");
  const [apiResult, setApiResult] = useState(null);
  const [apiLoading, setApiLoading] = useState(false);

  // Presets
  const allPresets = [...savedPresets, ...customPresets];

  // Fetch API objectives on mount (includes QAOA on IBM Quantum)
  useEffect(() => {
    getObjectives().then((d) => setApiObjectives(d?.objectives || [])).catch(() => {});
  }, []);

  // Run backend optimization (e.g. QAOA on IBM Quantum)
  const runApiOptimization = async () => {
    setApiResult(null);
    setApiLoading(true);
    const tickers = customTickerList && customTickerList.length >= nAssets
      ? customTickerList.slice(0, nAssets)
      : DEFAULT_TICKERS.slice(0, nAssets);
    const end = new Date();
    const start = new Date();
    start.setFullYear(start.getFullYear() - 1);
    try {
      const result = await optimizePortfolio({
        tickers,
        start_date: start.toISOString().slice(0, 10),
        end_date: end.toISOString().slice(0, 10),
        objective: apiObjective,
        strategy_preset: "balanced",
      });
      setApiResult(result);
    } catch (e) {
      setApiResult({ error: e?.message || "Optimization failed" });
    } finally {
      setApiLoading(false);
    }
  };

  // Apply preset
  const applyPreset = (preset) => {
    setNAssets(preset.nAssets);
    setOmega(preset.omega);
    setEvolutionTime(preset.evolutionTime);
    setMaxWeight(preset.maxWeight);
    setRegime(preset.regime);
    if (preset.evolutionMethod) setEvolutionMethod(preset.evolutionMethod);
    if (preset.turnoverLimit) setTurnoverLimit(preset.turnoverLimit);
  };

  // Save custom preset
  const saveCustomPreset = () => {
    const newPreset = {
      name: `Preset ${customPresets.length + 1}`,
      nAssets,
      omega,
      evolutionTime,
      maxWeight,
      regime,
      evolutionMethod,
      turnoverLimit
    };
    setCustomPresets([...customPresets, newPreset]);
  };

  // Full theme palettes (all keys so text/buttons stay visible)
  const themePalettes = [
    {
      name: "Dark",
      bg: "#0A0E1A", surface: "#111827", surfaceLight: "#1A2235", border: "#1E293B", borderLight: "#2D3A52",
      text: "#E2E8F0", textMuted: "#94A3B8", textDim: "#64748B", accent: "#3B82F6", accentGlow: "rgba(59,130,246,0.2)",
      green: "#10B981", red: "#EF4444", orange: "#F59E0B", purple: "#8B5CF6", cyan: "#06B6D4", pink: "#EC4899",
    },
    {
      name: "Light",
      bg: "#F8FAFC", surface: "#FFFFFF", surfaceLight: "#F1F5F9", border: "#E2E8F0", borderLight: "#CBD5E1",
      text: "#0F172A", textMuted: "#475569", textDim: "#64748B", accent: "#2563EB", accentGlow: "rgba(37,99,235,0.12)",
      green: "#059669", red: "#DC2626", orange: "#D97706", purple: "#7C3AED", cyan: "#0891B2", pink: "#DB2777",
    },
    {
      name: "Ocean",
      bg: "#0F172A", surface: "#1E293B", surfaceLight: "#334155", border: "#334155", borderLight: "#475569",
      text: "#F1F5F9", textMuted: "#94A3B8", textDim: "#64748B", accent: "#0EA5E9", accentGlow: "rgba(14,165,233,0.2)",
      green: "#10B981", red: "#EF4444", orange: "#F59E0B", purple: "#8B5CF6", cyan: "#06B6D4", pink: "#EC4899",
    },
    {
      name: "Forest",
      bg: "#052E16", surface: "#064E3B", surfaceLight: "#065F46", border: "#047857", borderLight: "#059669",
      text: "#ECFDF5", textMuted: "#A7F3D0", textDim: "#6EE7B7", accent: "#10B981", accentGlow: "rgba(16,185,129,0.25)",
      green: "#34D399", red: "#F87171", orange: "#FBBF24", purple: "#A78BFA", cyan: "#22D3EE", pink: "#F472B6",
    },
    {
      name: "Sunset",
      bg: "#1A1A2E", surface: "#16213E", surfaceLight: "#1F3460", border: "#2D3561", borderLight: "#3D4A6F",
      text: "#E2E8F0", textMuted: "#94A3B8", textDim: "#64748B", accent: "#F59E0B", accentGlow: "rgba(245,158,11,0.2)",
      green: "#10B981", red: "#EF4444", orange: "#F59E0B", purple: "#8B5CF6", cyan: "#06B6D4", pink: "#EC4899",
    },
  ];
  const themes = themePalettes;

  // Apply theme: merge with default colors so we never have undefined (keeps text/buttons visible)
  const applyTheme = (theme) => {
    setActiveTheme({ ...colors, ...theme });
  };

  // Export function
  const handleExport = (format) => {
    alert(`Exporting in ${format.toUpperCase()} format. This would typically download a file.`);
  };

  // Drag and drop handlers
  const handleDragStart = (e, id) => {
    setIsDragging(id);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e, targetId) => {
    e.preventDefault();
    if (isDragging && isDragging !== targetId) {
      // Reorder logic would go here
      console.log(`Moved ${isDragging} to ${targetId}`);
    }
    setIsDragging(null);
  };

  // Parse custom tickers: "AAPL, MSFT, GOOG" -> ["AAPL","MSFT","GOOG"], empty = use default
  const customTickerList = useMemo(() => {
    if (!customTickersString || typeof customTickersString !== "string") return null;
    const list = customTickersString.split(/[\s,]+/).map(s => s.trim().toUpperCase()).filter(Boolean);
    return list.length > 0 ? list : null;
  }, [customTickersString]);

  // Compute
  const data = useMemo(() => {
    return generateMarketData(nAssets, 504, regime, dataSeed, customTickerList);
  }, [nAssets, regime, dataSeed, customTickerList]);

  // QSW optimization with selected method
  const qsw = useMemo(() => {
    if (!data || !data.assets || data.assets.length === 0) {
      return {weights:[],portReturn:0,portVol:0,sharpe:0,nActive:0};
    }
    
    if (evolutionMethod === 'annealing') {
      return runQuantumAnnealingOptimization(data, maxWeight);
    } else {
      return runQSWOptimization(data, omega, evolutionTime, maxWeight, turnoverLimit, evolutionMethod);
    }
  }, [data, omega, evolutionTime, maxWeight, turnoverLimit, evolutionMethod]);

  const benchmarks = useMemo(() => {
    if (!data || !data.assets) {
      return {equalWeight:{name:"Equal Weight",weights:[],portReturn:0,portVol:0,sharpe:0},minVariance:{name:"Min Variance",weights:[],portReturn:0,portVol:0,sharpe:0},riskParity:{name:"Risk Parity",weights:[],portReturn:0,portVol:0,sharpe:0},maxSharpe:{name:"Max Sharpe",weights:[],portReturn:0,portVol:0,sharpe:0}};
    }
    return runBenchmarks(data);
  }, [data]);

  const riskMetrics = useMemo(() => {
    if (!data || !qsw?.weights || qsw.weights.length === 0) {
      return {var95:0,cvar:0};
    }
    return computeVaR(data, qsw.weights, 0.95);
  }, [data, qsw.weights]);

  // Equity curves
  const equityCurves = useMemo(() => {
    const qswCurve = simulateEquityCurve(data, qsw.weights, 504);
    const ewCurve = simulateEquityCurve(data, benchmarks.equalWeight.weights, 504);
    const mvCurve = simulateEquityCurve(data, benchmarks.minVariance.weights, 504);
    const rpCurve = simulateEquityCurve(data, benchmarks.riskParity.weights, 504);
    const msCurve = simulateEquityCurve(data, benchmarks.maxSharpe.weights, 504);
    
    // Add additional quantum methods to the comparison
    let discreteWeights = [], decoherentWeights = [], annealingWeights = [];
    
    if (evolutionMethod !== 'discrete') {
      const discreteResult = runQSWOptimization(data, omega, evolutionTime, maxWeight, turnoverLimit, 'discrete');
      discreteWeights = discreteResult.weights;
    } else {
      discreteWeights = qsw.weights;
    }
    
    if (evolutionMethod !== 'decoherent') {
      const decoherentResult = runQSWOptimization(data, omega, evolutionTime, maxWeight, turnoverLimit, 'decoherent');
      decoherentWeights = decoherentResult.weights;
    } else {
      decoherentWeights = qsw.weights;
    }
    
    if (evolutionMethod !== 'annealing') {
      const annealingResult = runQuantumAnnealingOptimization(data, maxWeight);
      annealingWeights = annealingResult.weights;
    } else {
      annealingWeights = qsw.weights;
    }
    
    const discreteCurve = simulateEquityCurve(data, discreteWeights, 504);
    const decoherentCurve = simulateEquityCurve(data, decoherentWeights, 504);
    const annealingCurve = simulateEquityCurve(data, annealingWeights, 504);
    
    return qswCurve.map((pt, i) => ({
      day: pt.day,
      QSW: pt.value,
      "QSW-Discrete": discreteCurve[i]?.value || 100,
      "QSW-Decoherent": decoherentCurve[i]?.value || 100,
      "Quantum Annealing": annealingCurve[i]?.value || 100,
      "Equal Weight": ewCurve[i]?.value || 100,
      "Min Variance": mvCurve[i]?.value || 100,
      "Risk Parity": rpCurve[i]?.value || 100,
      "Max Sharpe": msCurve[i]?.value || 100,
    }));
  }, [data, qsw.weights, benchmarks, omega, evolutionTime, maxWeight, turnoverLimit]);

  // Holdings data
  const holdings = useMemo(() => {
    if (!data?.assets || !qsw?.weights) {
      return [];
    }
    return data.assets.map((a, i) => ({
      name: a.name,
      sector: a.sector,
      weight: (qsw.weights[i] || 0),
      annReturn: a.annReturn,
      annVol: a.annVol,
      sharpe: a.sharpe
    }))
      .filter(h => h.weight > 0.005)
      .sort((a, b) => b.weight - a.weight);
  }, [data, qsw]);

  // Sector allocation
  const sectorData = useMemo(() => {
    if (!holdings || holdings.length === 0) {
      return [];
    }
    const sectors = {};
    holdings.forEach(h => {
      const sector = h.sector || 'Unknown';
      sectors[sector] = (sectors[sector] || 0) + (h.weight || 0);
    });
    return Object.entries(sectors).map(([name, value]) => ({ name, value: Math.round(value * 1000) / 10 })).sort((a, b) => b.value - a.value);
  }, [holdings]);

  // Short name -> strategy key for filtering
  const strategyNameToKey = { "QSW": "QSW", "QSW-Discrete": "QSW-Discrete", "QSW-Decoherent": "QSW-Decoherent", "Quantum Annealing": "Quantum Annealing", "Equal Wt": "Equal Weight", "Min Var": "Min Variance", "Risk Par": "Risk Parity", "Max Shp": "Max Sharpe" };

  // Benchmark comparison with additional quantum methods (then filter by selectedStrategies)
  const benchmarkComparisonAll = useMemo(() => {
    const discreteResult = runQSWOptimization(data, omega, evolutionTime, maxWeight, turnoverLimit, 'discrete');
    const decoherentResult = runQSWOptimization(data, omega, evolutionTime, maxWeight, turnoverLimit, 'decoherent');
    const annealingResult = runQuantumAnnealingOptimization(data, maxWeight);
    return [
      { name: "QSW", sharpe: qsw.sharpe, return: qsw.portReturn * 100, vol: qsw.portVol * 100, nActive: qsw.nActive },
      { name: "QSW-Discrete", sharpe: discreteResult.sharpe, return: discreteResult.portReturn * 100, vol: discreteResult.portVol * 100, nActive: discreteResult.nActive },
      { name: "QSW-Decoherent", sharpe: decoherentResult.sharpe, return: decoherentResult.portReturn * 100, vol: decoherentResult.portVol * 100, nActive: decoherentResult.nActive },
      { name: "Quantum Annealing", sharpe: annealingResult.sharpe, return: annealingResult.portReturn * 100, vol: annealingResult.portVol * 100, nActive: annealingResult.nActive },
      { name: "Equal Wt", sharpe: benchmarks.equalWeight.sharpe, return: benchmarks.equalWeight.portReturn * 100, vol: benchmarks.equalWeight.portVol * 100, nActive: nAssets },
      { name: "Min Var", sharpe: benchmarks.minVariance.sharpe, return: benchmarks.minVariance.portReturn * 100, vol: benchmarks.minVariance.portVol * 100, nActive: nAssets },
      { name: "Risk Par", sharpe: benchmarks.riskParity.sharpe, return: benchmarks.riskParity.portReturn * 100, vol: benchmarks.riskParity.portVol * 100, nActive: nAssets },
      { name: "Max Shp", sharpe: benchmarks.maxSharpe.sharpe, return: benchmarks.maxSharpe.portReturn * 100, vol: benchmarks.maxSharpe.portVol * 100, nActive: nAssets },
    ];
  }, [qsw, benchmarks, data, omega, evolutionTime, maxWeight, turnoverLimit, nAssets]);

  const benchmarkComparison = useMemo(() => {
    return benchmarkComparisonAll.filter(row => selectedStrategies.has(strategyNameToKey[row.name] || row.name));
  }, [benchmarkComparisonAll, selectedStrategies]);

  // Risk-return scatter
  const riskReturnScatter = useMemo(() => {
    if (!data?.assets || !qsw?.weights) {
      return [];
    }
    return data.assets.map((a, i) => ({
      name: a.name,
      x: (a.annVol || 0) * 100,
      y: (a.annReturn || 0) * 100,
      z: ((qsw.weights[i] || 0) * 100),
      sector: a.sector || 'Unknown',
      inPortfolio: (qsw.weights[i] || 0) > 0.005
    }));
  }, [data, qsw]);

  // Calculate best benchmark for improvement calculation
  let bestBenchmarkSharpe = 0;
  if (benchmarks && benchmarks.equalWeight && benchmarks.minVariance && benchmarks.riskParity && benchmarks.maxSharpe) {
    bestBenchmarkSharpe = Math.max(
      benchmarks.equalWeight.sharpe, 
      benchmarks.minVariance.sharpe, 
      benchmarks.riskParity.sharpe, 
      benchmarks.maxSharpe.sharpe
    );
  }
  
  // Calculate improvement over best benchmark
  let sharpeImprovement = 0;
  if (bestBenchmarkSharpe === 0) {
    sharpeImprovement = 0;
  } else {
    sharpeImprovement = ((qsw.sharpe / bestBenchmarkSharpe) - 1) * 100;
  }

  return (
    <DashboardThemeContext.Provider value={activeTheme}>
    <div 
      role="main" 
      aria-label="Quantum Portfolio Optimization Dashboard" 
      style={{ 
        background: activeTheme.bg, 
        minHeight: "100vh", 
        color: activeTheme.text, 
        fontFamily: "'Space Grotesk', -apple-system, sans-serif",
        outline: 'none'
      }}
      tabIndex={0}
    >

      {/* ─── HEADER ─── */}
      <header style={{ borderBottom: `1px solid ${activeTheme.border}`, padding: "16px 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: `linear-gradient(135deg, ${activeTheme.accent}, ${activeTheme.purple})`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>⟨ψ⟩</div>
          <div>
            <h1 style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-0.02em", margin: 0 }}>{dashboardTitle}</h1>
            <p style={{ fontSize: 11, color: activeTheme.textDim, margin: "2px 0 0 0" }}>{dashboardSubtitle}</p>
          </div>
        </div>
        <nav role="navigation" aria-label="Dashboard navigation">
          <div style={{ display: "flex", gap: 4 }}>
            <CustomizableTabButton theme={activeTheme} active={activeTab === "portfolio"} onClick={() => setActiveTab("portfolio")} icon={<FaBriefcase size={14} />} aria-controls="portfolio-tab-panel">Portfolio</CustomizableTabButton>
            <CustomizableTabButton theme={activeTheme} active={activeTab === "performance"} onClick={() => setActiveTab("performance")} icon={<FaChartLine size={14} />} aria-controls="performance-tab-panel">Performance</CustomizableTabButton>
            <CustomizableTabButton theme={activeTheme} active={activeTab === "risk"} onClick={() => setActiveTab("risk")} icon={<FaShieldAlt size={14} />} aria-controls="risk-tab-panel">Risk</CustomizableTabButton>
            <CustomizableTabButton theme={activeTheme} active={activeTab === "sensitivity"} onClick={() => setActiveTab("sensitivity")} icon={<FaSlidersH size={14} />} aria-controls="sensitivity-tab-panel">Sensitivity</CustomizableTabButton>
          </div>
        </nav>
      </header>

      <div style={{ display: "flex", height: "calc(100vh - 65px)" }}>

        {/* ─── LEFT PANEL: CUSTOMIZABLE CONTROLS ─── */}
        <aside 
          role="complementary" 
          aria-label="Dashboard controls and settings" 
          style={{ 
            width: 320, 
            borderRight: `1px solid ${activeTheme.border}`, 
            padding: 20, 
            overflowY: "auto", 
            flexShrink: 0, 
            background: activeTheme.surfaceLight,
            outline: 'none'
          }}
          tabIndex={0}
        >
          
          {/* Dashboard Title Editor */}
          <InteractiveSectionTitle 
            children={dashboardTitle} 
            subtitle="Click to edit dashboard title" 
            onEdit={setDashboardTitle}
            editable={true}
          />
          
          <div style={{ height: 1, background: activeTheme.border, margin: "16px 0" }} />
          
          {/* Preset Selector */}
          <PresetSelector 
            presets={allPresets} 
            onSelect={applyPreset} 
            currentPreset={null} // Would need to track current preset
          />
          
          {/* Save Custom Preset Button */}
          <button 
            onClick={saveCustomPreset}
            style={{
              width: "100%",
              padding: "8px 0",
              background: activeTheme.accentGlow,
              border: `1px solid ${activeTheme.accent}`,
              borderRadius: 6,
              color: activeTheme.accent,
              fontSize: 11,
              cursor: "pointer",
              marginBottom: 16,
              fontFamily: "'JetBrains Mono', monospace",
              fontWeight: 600,
              outline: 'none'
            }}
            onFocus={(e) => {
              e.target.style.boxShadow = `0 0 0 ${colors.focusOutlineWidth} ${colors.focusOutline}`;
            }}
            onBlur={(e) => {
              e.target.style.boxShadow = 'none';
            }}
          >
            + Save Current Settings as Preset
          </button>
          
          {/* Theme Selector */}
          <ThemeSelector 
            themes={themes} 
            onSelect={applyTheme} 
            currentTheme={activeTheme} 
          />
          
          <div style={{ height: 1, background: activeTheme.border, margin: "16px 0" }} />
          
          {/* Export Controls */}
          <ExportControls onExport={handleExport} />
          
          <div style={{ height: 1, background: activeTheme.border, margin: "16px 0" }} />
          
          {/* Quantum Parameters */}
          <div style={{ fontSize: 10, color: activeTheme.textDim, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12, fontFamily: "'JetBrains Mono', monospace" }}>Quantum Parameters</div>

          <CustomizableSlider 
            label="Omega (ω)" 
            value={omega} 
            onChange={setOmega} 
            min={0.05} 
            max={0.60} 
            step={0.01} 
            info="Mixing parameter: quantum potential vs. graph coupling" 
            customColor={activeTheme.accent}
          />
          <CustomizableSlider 
            label="Evolution Time" 
            value={evolutionTime} 
            onChange={setEvolutionTime} 
            min={1} 
            max={50} 
            step={1} 
            info="Higher = more smoothing, lower = more differentiation" 
            customColor={activeTheme.accent}
          />

          <div style={{ height: 1, background: activeTheme.border, margin: "16px 0" }} />
          <div style={{ fontSize: 10, color: activeTheme.textDim, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12, fontFamily: "'JetBrains Mono', monospace" }}>Evolution Method</div>
          
          <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
            {[
              { key: "continuous", label: "Continuous", icon: <FaCircle size={14} />, color: activeTheme.accent },
              { key: "discrete", label: "Discrete", icon: <FaRegCircle size={14} />, color: activeTheme.purple },
              { key: "decoherent", label: "Decoherent", icon: <FaAdjust size={14} />, color: activeTheme.cyan },
              { key: "annealing", label: "Annealing", icon: <FaBolt size={14} />, color: activeTheme.pink },
            ].map(m => (
              <button 
                key={m.key} 
                onClick={() => setEvolutionMethod(m.key)} 
                style={{
                  flex: 1, 
                  padding: "8px 4px", 
                  background: evolutionMethod === m.key ? `${m.color}18` : "transparent",
                  border: `1px solid ${evolutionMethod === m.key ? m.color : activeTheme.border}`, 
                  borderRadius: 6,
                  color: evolutionMethod === m.key ? m.color : activeTheme.textDim, 
                  fontSize: 11, 
                  cursor: "pointer",
                  fontFamily: "'JetBrains Mono', monospace", 
                  transition: "all 0.2s", 
                  textAlign: "center",
                  outline: 'none'
                }}
                onFocus={(e) => {
                  e.target.style.boxShadow = `0 0 0 ${colors.focusOutlineWidth} ${colors.focusOutline}`;
                }}
                onBlur={(e) => {
                  e.target.style.boxShadow = 'none';
                }}
              >
                <div style={{ fontSize: 16 }}>{m.icon}</div>
                <div style={{ marginTop: 2 }}>{m.label}</div>
              </button>
            ))}
          </div>

          <div style={{ height: 1, background: activeTheme.border, margin: "16px 0" }} />
          <div style={{ fontSize: 10, color: activeTheme.textDim, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12, fontFamily: "'JetBrains Mono', monospace" }}>Market Regime</div>
          
          <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
            {[
              { key: "normal", label: "Normal", icon: <FaDotCircle size={14} />, color: activeTheme.accent },
              { key: "bull", label: "Bull", icon: <FaCaretUp size={14} />, color: activeTheme.green },
              { key: "bear", label: "Bear", icon: <FaCaretDown size={14} />, color: activeTheme.red },
              { key: "volatile", label: "Volatile", icon: <FaChartLine size={14} />, color: activeTheme.orange },
            ].map(r => (
              <button 
                key={r.key} 
                onClick={() => setRegime(r.key)} 
                style={{
                  flex: 1, 
                  padding: "8px 4px", 
                  background: regime === r.key ? `${r.color}18` : "transparent",
                  border: `1px solid ${regime === r.key ? r.color : activeTheme.border}`, 
                  borderRadius: 6,
                  color: regime === r.key ? r.color : activeTheme.textDim, 
                  fontSize: 11, 
                  cursor: "pointer",
                  fontFamily: "'JetBrains Mono', monospace", 
                  transition: "all 0.2s", 
                  textAlign: "center",
                  outline: 'none'
                }}
                onFocus={(e) => {
                  e.target.style.boxShadow = `0 0 0 ${colors.focusOutlineWidth} ${colors.focusOutline}`;
                }}
                onBlur={(e) => {
                  e.target.style.boxShadow = 'none';
                }}
              >
                <div style={{ fontSize: 16 }}>{r.icon}</div>
                <div style={{ marginTop: 2 }}>{r.label}</div>
              </button>
            ))}
          </div>

          <div style={{ height: 1, background: activeTheme.border, margin: "16px 0" }} />
          <div style={{ fontSize: 10, color: activeTheme.textDim, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12, fontFamily: "'JetBrains Mono', monospace" }}>Constraints</div>

          <CustomizableSlider 
            label="Max Weight" 
            value={maxWeight} 
            onChange={setMaxWeight} 
            min={0.03} 
            max={0.30} 
            step={0.01} 
            unit="%" 
            info="Maximum allocation per position" 
            customColor={activeTheme.accent}
          />
          <CustomizableSlider 
            label="Max Turnover" 
            value={turnoverLimit} 
            onChange={setTurnoverLimit} 
            min={0.05} 
            max={0.50} 
            step={0.01} 
            info="Maximum portfolio turnover per rebalance" 
            customColor={activeTheme.accent}
          />
          <CustomizableSlider 
            label="Universe Size" 
            value={nAssets} 
            onChange={setNAssets} 
            min={5} 
            max={30} 
            step={1} 
            unit=" assets" 
            info="Number of assets in investable universe" 
            customColor={activeTheme.accent}
          />

          <div style={{ height: 1, background: activeTheme.border, margin: "16px 0" }} />
          <div style={{ fontSize: 10, color: activeTheme.textDim, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12, fontFamily: "'JetBrains Mono', monospace" }}>Custom Tickers</div>
          <input
            type="text"
            value={customTickersString}
            onChange={(e) => setCustomTickersString(e.target.value)}
            placeholder="e.g. AAPL, MSFT, GOOGL (empty = default)"
            aria-label="Custom ticker symbols, comma-separated"
            style={{
              width: "100%", padding: "8px 10px", marginBottom: 4, borderRadius: 6, border: `1px solid ${activeTheme.border}`,
              background: activeTheme.surface, color: activeTheme.text, fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
              outline: "none", boxSizing: "border-box"
            }}
          />
          <div style={{ fontSize: 10, color: activeTheme.textDim, marginBottom: 12 }}>Override asset symbols. Count must match Universe Size or use first N.</div>

          <div style={{ height: 1, background: activeTheme.border, margin: "16px 0" }} />
          <div style={{ fontSize: 10, color: activeTheme.textDim, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12, fontFamily: "'JetBrains Mono', monospace" }}>Strategies to Compare</div>
          {["QSW", "QSW-Discrete", "QSW-Decoherent", "Quantum Annealing", "Equal Weight", "Min Variance", "Risk Parity", "Max Sharpe"].map(key => (
            <label key={key} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, cursor: "pointer", fontSize: 12, color: activeTheme.text }}>
              <input
                type="checkbox"
                checked={selectedStrategies.has(key)}
                onChange={() => {
                  setSelectedStrategies(prev => {
                    const next = new Set(prev);
                    if (next.has(key)) next.delete(key); else next.add(key);
                    return next;
                  });
                }}
                style={{ accentColor: activeTheme.accent, width: 16, height: 16 }}
              />
              <span>{key}</span>
            </label>
          ))}

          <div style={{ height: 1, background: activeTheme.border, margin: "16px 0" }} />
          <div style={{ fontSize: 10, color: activeTheme.textDim, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12, fontFamily: "'JetBrains Mono', monospace" }}>Live API (IBM QAOA, etc.)</div>
          <div style={{ fontSize: 10, color: activeTheme.textMuted, marginBottom: 8 }}>Run optimization on backend with real market data.</div>
          <select
            value={apiObjective}
            onChange={(e) => setApiObjective(e.target.value)}
            style={{
              width: "100%", padding: "8px 10px", marginBottom: 8, borderRadius: 6, border: `1px solid ${activeTheme.border}`,
              background: activeTheme.surface, color: activeTheme.text, fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
              outline: "none", boxSizing: "border-box", cursor: "pointer"
            }}
            aria-label="Optimization objective"
          >
            {apiObjectives.length > 0 ? (
              apiObjectives.map((o) => (
                <option key={o.id} value={o.id}>{o.name}</option>
              ))
            ) : (
              <>
                <option value="max_sharpe">Max Sharpe Ratio</option>
                <option value="min_variance">Min Variance</option>
                <option value="qaoa_ibm">QAOA on IBM Quantum</option>
                <option value="hrp">Hierarchical Risk Parity</option>
                <option value="risk_parity">Risk Parity</option>
              </>
            )}
          </select>
          <button
            onClick={runApiOptimization}
            disabled={apiLoading}
            style={{
              width: "100%", padding: "10px", background: apiLoading ? activeTheme.border : activeTheme.accent,
              border: "none", borderRadius: 6, color: activeTheme.bg, fontSize: 12, fontWeight: 600,
              cursor: apiLoading ? "not-allowed" : "pointer", fontFamily: "'JetBrains Mono', monospace"
            }}
          >
            {apiLoading ? "Running…" : "Run API Optimization"}
          </button>
          {apiResult?.error && (
            <div style={{ fontSize: 11, color: activeTheme.red, marginTop: 8 }}>{apiResult.error}</div>
          )}
          {apiResult && !apiResult.error && (
            <div style={{ fontSize: 11, color: activeTheme.green, marginTop: 8 }}>
              {apiResult.backend_type ? `Backend: ${apiResult.backend_type}` : ""} Sharpe: {((apiResult.sharpe_ratio ?? apiResult.qsw_result?.sharpe_ratio) || 0).toFixed(3)}
            </div>
          )}

          <div style={{ height: 1, background: activeTheme.border, margin: "16px 0" }} />
          <div style={{ fontSize: 10, color: activeTheme.textDim, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12, fontFamily: "'JetBrains Mono', monospace" }}>Simulation</div>
          <CustomizableSlider 
            label="Random Seed" 
            value={dataSeed} 
            onChange={setDataSeed} 
            min={1} 
            max={999} 
            step={1} 
            info="Change to generate different market scenarios" 
            customColor={activeTheme.accent}
          />
          
          <button
            onClick={() => { 
              setOmega(0.30); 
              setEvolutionTime(10); 
              setEvolutionMethod('continuous'); 
              setMaxWeight(0.10); 
              setTurnoverLimit(0.20); 
              setNAssets(20); 
              setRegime("normal"); 
              setDataSeed(42); 
            }}
            style={{ 
              width: "100%", 
              padding: "8px 0", 
              background: "transparent", 
              border: `1px solid ${activeTheme.border}`, 
              borderRadius: 6, 
              color: activeTheme.textMuted, 
              fontSize: 11, 
              cursor: "pointer", 
              marginTop: 8, 
              fontFamily: "'JetBrains Mono', monospace",
              outline: 'none'
            }}
            onFocus={(e) => {
              e.target.style.boxShadow = `0 0 0 ${colors.focusOutlineWidth} ${colors.focusOutline}`;
            }}
            onBlur={(e) => {
              e.target.style.boxShadow = 'none';
            }}
          >
            <FaUndo size={12} style={{ display: "inline", verticalAlign: "middle", marginRight: 6 }} />
            Reset All Parameters
          </button>
        </aside>

        {/* ─── MAIN CONTENT ─── */}
        <main style={{ flex: 1, overflowY: "auto", padding: 24 }} role="tabpanel" aria-labelledby={`${activeTab}-tab`} id={`${activeTab}-tab-panel`}>

          {/* ─── DRAGGABLE METRIC CARDS (always visible) ─── */}
          <section aria-label="Key portfolio metrics" style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
            <DraggableMetricCard 
              label="Sharpe Ratio" 
              value={qsw?.sharpe !== undefined ? qsw.sharpe.toFixed(3) : "0.000"} 
              color={(qsw?.sharpe || 0) > bestBenchmarkSharpe ? activeTheme.green : activeTheme.orange} 
              delta={sharpeImprovement} 
              description="Risk-adjusted return" 
              onDrag={(e) => handleDragStart(e, 'sharpe')}
              onDrop={(e) => handleDrop(e, 'sharpe')}
            />
            <DraggableMetricCard 
              label="Expected Return" 
              value={qsw?.portReturn !== undefined ? (qsw.portReturn * 100).toFixed(1) : "0.0"} 
              unit="%" 
              color={activeTheme.accent} 
              description="Annualized" 
              onDrag={(e) => handleDragStart(e, 'return')}
              onDrop={(e) => handleDrop(e, 'return')}
            />
            <DraggableMetricCard 
              label="Volatility" 
              value={qsw?.portVol !== undefined ? (qsw.portVol * 100).toFixed(1) : "0.0"} 
              unit="%" 
              color={activeTheme.orange} 
              description="Annualized" 
              onDrag={(e) => handleDragStart(e, 'volatility')}
              onDrop={(e) => handleDrop(e, 'volatility')}
            />
            <DraggableMetricCard 
              label="Active Positions" 
              value={qsw?.nActive !== undefined ? qsw.nActive : 0} 
              unit={`/ ${nAssets}`} 
              color={activeTheme.purple} 
              description="Above 0.5% weight" 
              onDrag={(e) => handleDragStart(e, 'positions')}
              onDrop={(e) => handleDrop(e, 'positions')}
            />
            <DraggableMetricCard 
              label="Daily VaR (95%)" 
              value={riskMetrics?.var95 !== undefined ? riskMetrics.var95.toFixed(2) : "0.00"} 
              unit="%" 
              color={activeTheme.red} 
              description="Max daily loss at 95% CI" 
              onDrag={(e) => handleDragStart(e, 'var')}
              onDrop={(e) => handleDrop(e, 'var')}
            />
          </section>

          {/* ─── PORTFOLIO TAB ─── */}
          {activeTab === "portfolio" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
              {/* Holdings */}
              <div style={{ background: activeTheme.surface, border: `1px solid ${activeTheme.border}`, borderRadius: 10, padding: 20 }}>
                <InteractiveSectionTitle 
                  children="Portfolio Holdings" 
                  subtitle={`${holdings?.length || 0} positions above 0.5%`} 
                  onEdit={(newTitle) => console.log('Holdings section renamed to:', newTitle)}
                  editable={true}
                />
                <div style={{ maxHeight: 380, overflowY: "auto" }}>
                  {holdings && holdings.length > 0 ? holdings.map((h, i) => {
                    const weight = h.weight || 0;
                    const weightPercent = maxWeight > 0 ? Math.min((weight / maxWeight) * 100, 100) : 0;
                    const key = h.name || `holding_${i}`;
                    return (
                      <div key={key} style={{ display: "flex", alignItems: "center", padding: "6px 0", borderBottom: `1px solid ${activeTheme.border}`, gap: 10 }}>
                        <span style={{ width: 18, fontSize: 10, color: activeTheme.textDim, fontFamily: "'JetBrains Mono', monospace" }}>{i + 1}</span>
                        <div style={{ flex: 1 }}>
                          <span style={{ fontSize: 13, fontWeight: 600, color: activeTheme.text }}>{h.name || 'Unknown'}</span>
                          <span style={{ fontSize: 10, color: activeTheme.textDim, marginLeft: 6 }}>{h.sector || 'Unknown'}</span>
                        </div>
                        <div style={{ width: 80 }}>
                          <div style={{ height: 4, background: activeTheme.border, borderRadius: 2, overflow: "hidden" }}>
                            <div style={{ height: "100%", width: `${weightPercent}%`, background: chartColors[i % chartColors.length], borderRadius: 2 }} />
                          </div>
                        </div>
                        <span style={{ width: 50, textAlign: "right", fontSize: 12, fontWeight: 600, color: activeTheme.accent, fontFamily: "'JetBrains Mono', monospace" }}>{(weight * 100).toFixed(1)}%</span>
                      </div>
                    );
                  }) : (
                    <div style={{ padding: 40, textAlign: "center", color: activeTheme.textDim }}>
                      No holdings data available
                    </div>
                  )}
                </div>
              </div>

              {/* Sector Allocation */}
              <div style={{ background: activeTheme.surface, border: `1px solid ${activeTheme.border}`, borderRadius: 10, padding: 20 }}>
                <InteractiveSectionTitle 
                  children="Sector Breakdown" 
                  subtitle="Allocation by GICS sector" 
                  onEdit={(newTitle) => console.log('Sector section renamed to:', newTitle)}
                  editable={true}
                />
                {sectorData && sectorData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie data={sectorData} cx="50%" cy="50%" innerRadius={60} outerRadius={110} dataKey="value" nameKey="name" stroke={activeTheme.bg} strokeWidth={2}>
                        {sectorData.map((_, i) => <Cell key={i} fill={chartColors[i % chartColors.length]} />)}
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                      <Legend wrapperStyle={{ fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }} formatter={(value) => <span style={{ color: activeTheme.text, fontSize: 12 }}>{value}</span>} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ height: 300, display: "flex", alignItems: "center", justifyContent: "center", color: activeTheme.textDim }}>
                    No sector data available
                  </div>
                )}
              </div>

              {/* Risk-Return Scatter */}
              <div style={{ background: activeTheme.surface, border: `1px solid ${activeTheme.border}`, borderRadius: 10, padding: 20, gridColumn: "1 / -1" }}>
                <InteractiveSectionTitle 
                  children="Risk-Return Map" 
                  subtitle="Bubble size = portfolio weight. Blue = in portfolio, gray = excluded." 
                  onEdit={(newTitle) => console.log('Risk-Return section renamed to:', newTitle)}
                  editable={true}
                />
                {riskReturnScatter && riskReturnScatter.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={activeTheme.border} />
                    <XAxis dataKey="x" name="Volatility" unit="%" stroke={activeTheme.text} tick={{ fontSize: 12, fill: activeTheme.text }} label={{ value: "Volatility (%)", position: "bottom", fill: activeTheme.text, fontSize: 12 }} />
                    <YAxis dataKey="y" name="Return" unit="%" stroke={activeTheme.text} tick={{ fontSize: 12, fill: activeTheme.text }} label={{ value: "Return (%)", angle: -90, position: "left", fill: activeTheme.text, fontSize: 12 }} />
                    <Tooltip content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const d = payload[0]?.payload;
                      if (!d) return null;
                      return (
                        <div style={{ background: activeTheme.surfaceLight, border: `1px solid ${activeTheme.borderLight}`, borderRadius: 6, padding: "8px 12px", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>
                          <div style={{ color: activeTheme.text, fontWeight: 700 }}>{d.name || 'Unknown'} ({d.sector || 'Unknown'})</div>
                          <div style={{ color: activeTheme.textMuted }}>Return: {(typeof d.y === 'number' ? d.y.toFixed(1) : '0.0')}% | Vol: {(typeof d.x === 'number' ? d.x.toFixed(1) : '0.0')}%</div>
                          <div style={{ color: activeTheme.accent }}>Weight: {(typeof d.z === 'number' ? d.z.toFixed(1) : '0.0')}%</div>
                        </div>
                      );
                    }} />
                    <Scatter data={riskReturnScatter.filter(d => !d.inPortfolio)} fill={activeTheme.textDim} fillOpacity={0.3} shape="circle">
                      {riskReturnScatter.filter(d => !d.inPortfolio).map((_, i) => <Cell key={i} r={4} />)}
                    </Scatter>
                    <Scatter data={riskReturnScatter.filter(d => d.inPortfolio)} fill={activeTheme.accent}>
                      {riskReturnScatter.filter(d => d.inPortfolio).map((d, i) => <Cell key={i} r={Math.max(4, (typeof d.z === 'number' ? d.z * 1.5 : 4))} fillOpacity={0.8} />)}
                    </Scatter>
                    </ScatterChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ height: 300, display: "flex", alignItems: "center", justifyContent: "center", color: activeTheme.textDim }}>
                    No risk-return data available
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ─── PERFORMANCE TAB ─── */}
          {activeTab === "performance" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 20 }}>
              {/* Equity Curves */}
              <div style={{ background: activeTheme.surface, border: `1px solid ${activeTheme.border}`, borderRadius: 10, padding: 20 }}>
                <InteractiveSectionTitle 
                  children="Cumulative Performance vs. Benchmarks" 
                  subtitle="Simulated 2-year equity curve starting at $100" 
                  onEdit={(newTitle) => console.log('Performance section renamed to:', newTitle)}
                  editable={true}
                />
                {equityCurves && equityCurves.length > 0 ? (
                  <ResponsiveContainer width="100%" height={350}>
                    <LineChart data={equityCurves} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={activeTheme.border} />
                    <XAxis dataKey="day" stroke={activeTheme.text} tick={{ fontSize: 12, fill: activeTheme.text }} label={{ value: "Trading Days", position: "bottom", fill: activeTheme.text, fontSize: 12 }} />
                    <YAxis stroke={activeTheme.text} tick={{ fontSize: 12, fill: activeTheme.text }} label={{ value: "Portfolio Value ($)", angle: -90, position: "left", fill: activeTheme.text, fontSize: 12 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 12 }} formatter={(value) => <span style={{ color: activeTheme.text, fontSize: 12 }}>{value}</span>} />
                    <ReferenceLine y={100} stroke={activeTheme.textDim} strokeDasharray="3 3" />
                    {selectedStrategies.has("QSW") && <Line type="monotone" dataKey="QSW" stroke={benchmarkColors["QSW"]} strokeWidth={2.5} dot={false} name="QSW" />}
                    {selectedStrategies.has("QSW-Discrete") && <Line type="monotone" dataKey="QSW-Discrete" stroke={benchmarkColors["QSW-Discrete"]} strokeWidth={1.5} dot={false} strokeDasharray="4 2" />}
                    {selectedStrategies.has("QSW-Decoherent") && <Line type="monotone" dataKey="QSW-Decoherent" stroke={benchmarkColors["QSW-Decoherent"]} strokeWidth={1.5} dot={false} strokeDasharray="4 2" />}
                    {selectedStrategies.has("Quantum Annealing") && <Line type="monotone" dataKey="Quantum Annealing" stroke={benchmarkColors["Quantum Annealing"]} strokeWidth={1.5} dot={false} strokeDasharray="4 2" />}
                    {selectedStrategies.has("Equal Weight") && <Line type="monotone" dataKey="Equal Weight" stroke={benchmarkColors["Equal Weight"]} strokeWidth={1.5} dot={false} strokeDasharray="4 2" />}
                    {selectedStrategies.has("Min Variance") && <Line type="monotone" dataKey="Min Variance" stroke={benchmarkColors["Min Variance"]} strokeWidth={1.5} dot={false} strokeDasharray="4 2" />}
                    {selectedStrategies.has("Risk Parity") && <Line type="monotone" dataKey="Risk Parity" stroke={benchmarkColors["Risk Parity"]} strokeWidth={1.5} dot={false} strokeDasharray="4 2" />}
                    {selectedStrategies.has("Max Sharpe") && <Line type="monotone" dataKey="Max Sharpe" stroke={benchmarkColors["Max Sharpe"]} strokeWidth={1.5} dot={false} strokeDasharray="4 2" />}
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ height: 350, display: "flex", alignItems: "center", justifyContent: "center", color: activeTheme.textDim }}>
                    No equity curve data available
                  </div>
                )}
              </div>

              {/* Benchmark Comparison Table */}
              <div style={{ background: activeTheme.surface, border: `1px solid ${activeTheme.border}`, borderRadius: 10, padding: 20 }}>
                <InteractiveSectionTitle 
                  children="Strategy Comparison" 
                  subtitle="Side-by-side comparison of all strategies" 
                  onEdit={(newTitle) => console.log('Benchmark section renamed to:', newTitle)}
                  editable={true}
                />
                {benchmarkComparison && benchmarkComparison.length > 0 ? (
                  <>
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart data={benchmarkComparison} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={activeTheme.border} />
                    <XAxis dataKey="name" stroke={activeTheme.text} tick={{ fontSize: 12, fill: activeTheme.text }} />
                    <YAxis stroke={activeTheme.text} tick={{ fontSize: 12, fill: activeTheme.text }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="sharpe" name="Sharpe" fill={activeTheme.accent} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="return" name="Return %" fill={activeTheme.green} radius={[4, 4, 0, 0]} />
                        <Bar dataKey="vol" name="Vol %" fill={activeTheme.orange} radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>

                    {/* Table */}
                    <div style={{ marginTop: 16, overflowX: "auto" }}>
                      <table 
                        role="table" 
                        aria-label="Strategy comparison table" 
                        style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}
                      >
                        <thead>
                          <tr>{["Strategy", "Sharpe", "Return", "Volatility", "Positions"].map(h => (
                            <th key={h} style={{ padding: "8px 12px", textAlign: "left", borderBottom: `1px solid ${activeTheme.border}`, color: activeTheme.textDim, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</th>
                          ))}</tr>
                        </thead>
                        <tbody>
                          {benchmarkComparison.map((b, i) => {
                            const isQSW = b.name.includes("QSW") || b.name.includes("Quantum");
                            const maxSharpe = Math.max(...benchmarkComparison.map(x => (x.sharpe || 0)));
                            const isBest = (b.sharpe || 0) >= maxSharpe - 0.001;
                            return (
                              <tr 
                                key={b.name || i} 
                                style={{ background: isQSW ? activeTheme.accentGlow : "transparent" }}
                                role="row"
                              >
                                <td style={{ padding: "8px 12px", borderBottom: `1px solid ${activeTheme.border}`, fontWeight: isQSW ? 700 : 400, color: isQSW ? activeTheme.accent : activeTheme.text }}>{b.name || "Unknown"} {isBest && <FaStar size={12} style={{ color: activeTheme.accent, display: "inline", verticalAlign: "middle" }} />}</td>
                                <td style={{ padding: "8px 12px", borderBottom: `1px solid ${activeTheme.border}`, color: isBest ? activeTheme.green : activeTheme.text }}>{(b.sharpe || 0).toFixed(3)}</td>
                                <td style={{ padding: "8px 12px", borderBottom: `1px solid ${activeTheme.border}` }}>{(b.return || 0).toFixed(1)}%</td>
                                <td style={{ padding: "8px 12px", borderBottom: `1px solid ${activeTheme.border}` }}>{(b.vol || 0).toFixed(1)}%</td>
                                <td style={{ padding: "8px 12px", borderBottom: `1px solid ${activeTheme.border}` }}>{b.nActive || 0}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </>
                ) : (
                  <div style={{ padding: 40, textAlign: "center", color: activeTheme.textDim }}>
                    No benchmark comparison data available
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ─── RISK TAB ─── */}
          {activeTab === "risk" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
              {/* VaR Gauge */}
              <div style={{ background: activeTheme.surface, border: `1px solid ${activeTheme.border}`, borderRadius: 10, padding: 20 }}>
                <InteractiveSectionTitle 
                  children="Value at Risk" 
                  subtitle="Historical simulation, 95% confidence" 
                  onEdit={(newTitle) => console.log('VaR section renamed to:', newTitle)}
                  editable={true}
                />
                <div style={{ display: "flex", gap: 20, justifyContent: "center", padding: "20px 0" }}>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 10, color: activeTheme.textDim, textTransform: "uppercase", marginBottom: 8 }}>Daily VaR</div>
                    <div style={{ width: 120, height: 120, borderRadius: "50%", border: `4px solid ${activeTheme.orange}`, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", background: `${activeTheme.orange}10` }}>
                      <div style={{ fontSize: 28, fontWeight: 700, color: activeTheme.orange, fontFamily: "'JetBrains Mono', monospace" }}>{riskMetrics.var95.toFixed(2)}%</div>
                      <div style={{ fontSize: 9, color: activeTheme.textDim }}>of portfolio</div>
                    </div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 10, color: activeTheme.textDim, textTransform: "uppercase", marginBottom: 8 }}>Daily CVaR (ES)</div>
                    <div style={{ width: 120, height: 120, borderRadius: "50%", border: `4px solid ${activeTheme.red}`, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", background: `${activeTheme.red}10` }}>
                      <div style={{ fontSize: 28, fontWeight: 700, color: activeTheme.red, fontFamily: "'JetBrains Mono', monospace" }}>{riskMetrics.cvar.toFixed(2)}%</div>
                      <div style={{ fontSize: 9, color: activeTheme.textDim }}>expected shortfall</div>
                    </div>
                  </div>
                </div>
                <div style={{ fontSize: 11, color: activeTheme.textDim, textAlign: "center", marginTop: 8 }}>
                  On a $1M portfolio: VaR = ${((riskMetrics?.var95 || 0) * 10000).toFixed(0)} | CVaR = ${((riskMetrics?.cvar || 0) * 10000).toFixed(0)} daily
                </div>
              </div>

              {/* Factor Exposure (radar) */}
              <div style={{ background: activeTheme.surface, border: `1px solid ${activeTheme.border}`, borderRadius: 10, padding: 20 }}>
                <InteractiveSectionTitle 
                  children="Factor Risk Decomposition" 
                  subtitle="Approximate factor loadings" 
                  onEdit={(newTitle) => console.log('Factor section renamed to:', newTitle)}
                  editable={true}
                />
                <ResponsiveContainer width="100%" height={280}>
                  <RadarChart data={[
                    { factor: "Market", qsw: 0.7 + omega * 0.5, benchmark: 1.0 },
                    { factor: "Size", qsw: 0.3 + (1 - maxWeight) * 0.8, benchmark: 0.5 },
                    { factor: "Value", qsw: 0.4 + (1 - omega) * 0.4, benchmark: 0.4 },
                    { factor: "Momentum", qsw: 0.5 + omega * 0.3, benchmark: 0.3 },
                    { factor: "Quality", qsw: 0.6 + evolutionTime / 100, benchmark: 0.5 },
                    { factor: "Low Vol", qsw: 0.8 - omega * 0.5, benchmark: 0.3 },
                  ]}>
                    <PolarGrid stroke={activeTheme.border} />
                    <PolarAngleAxis dataKey="factor" tick={{ fill: activeTheme.text, fontSize: 12 }} />
                    <PolarRadiusAxis tick={false} axisLine={false} />
                    <Radar name="QSW" dataKey="qsw" stroke={activeTheme.accent} fill={activeTheme.accent} fillOpacity={0.2} strokeWidth={2} />
                    <Radar name="Benchmark" dataKey="benchmark" stroke={activeTheme.textDim} fill={activeTheme.textDim} fillOpacity={0.05} strokeWidth={1} strokeDasharray="4 2" />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>

              {/* Stress Test */}
              <div style={{ background: activeTheme.surface, border: `1px solid ${activeTheme.border}`, borderRadius: 10, padding: 20, gridColumn: "1 / -1" }}>
                <InteractiveSectionTitle 
                  children="Stress Test Scenarios" 
                  subtitle="Estimated portfolio impact under historical crisis scenarios" 
                  onEdit={(newTitle) => console.log('Stress test section renamed to:', newTitle)}
                  editable={true}
                />
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginTop: 12 }}>
                  {[
                    { name: "2008 GFC", shock: -0.50, vol: 0.80, desc: "Lehman collapse, credit freeze" },
                    { name: "COVID Crash", shock: -0.34, vol: 0.65, desc: "23-day selloff, March 2020" },
                    { name: "2022 Rate Shock", shock: -0.25, vol: 0.35, desc: "Fed tightening, growth selloff" },
                    { name: "Flash Crash", shock: -0.09, vol: 0.90, desc: "Intraday chaos, May 2010" },
                  ].map(scenario => {
                    const portVol = qsw?.portVol || 0;
                    const portImpact = scenario.shock * (0.5 + portVol * 3) * 100;
                    const portImpactValue = isNaN(portImpact) ? 0 : portImpact;
                    return (
                      <div key={scenario.name} style={{ background: activeTheme.surfaceLight, border: `1px solid ${activeTheme.border}`, borderRadius: 8, padding: 14 }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: activeTheme.text, marginBottom: 4 }}>{scenario.name}</div>
                        <div style={{ fontSize: 9, color: activeTheme.textDim, marginBottom: 10 }}>{scenario.desc}</div>
                        <div style={{ fontSize: 24, fontWeight: 700, color: activeTheme.red, fontFamily: "'JetBrains Mono', monospace" }}>{portImpactValue.toFixed(1)}%</div>
                        <div style={{ fontSize: 10, color: activeTheme.textDim }}>Est. portfolio loss</div>
                        <div style={{ marginTop: 8, height: 4, background: activeTheme.border, borderRadius: 2, overflow: "hidden" }}>
                          <div style={{ height: "100%", width: `${Math.min(Math.abs(portImpactValue), 60)}%`, background: activeTheme.red, borderRadius: 2 }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* ─── SENSITIVITY TAB ─── */}
          {activeTab === "sensitivity" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
              {/* Evolution Method Comparison */}
              <div style={{ background: activeTheme.surface, border: `1px solid ${activeTheme.border}`, borderRadius: 10, padding: 20 }}>
                <InteractiveSectionTitle 
                  children="Quantum Method Comparison" 
                  subtitle="Performance comparison of different quantum evolution methods" 
                  onEdit={(newTitle) => console.log('Method comparison section renamed to:', newTitle)}
                  editable={true}
                />
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={[
                    { method: "Continuous", sharpe: qsw.sharpe, return: qsw.portReturn * 100, vol: qsw.portVol * 100 },
                    { method: "Discrete", ...runQSWOptimization(data, omega, evolutionTime, maxWeight, turnoverLimit, 'discrete') },
                    { method: "Decoherent", ...runQSWOptimization(data, omega, evolutionTime, maxWeight, turnoverLimit, 'decoherent') },
                    { method: "Annealing", ...runQuantumAnnealingOptimization(data, maxWeight) }
                  ]} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={activeTheme.border} />
                    <XAxis dataKey="method" stroke={activeTheme.textDim} tick={{ fontSize: 11, fill: activeTheme.textMuted }} />
                    <YAxis stroke={activeTheme.textDim} tick={{ fontSize: 10, fill: activeTheme.textDim }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="sharpe" name="Sharpe" fill={activeTheme.accent} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="return" name="Return %" fill={activeTheme.green} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="vol" name="Vol %" fill={activeTheme.orange} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Omega Sensitivity */}
              <div style={{ background: activeTheme.surface, border: `1px solid ${activeTheme.border}`, borderRadius: 10, padding: 20 }}>
                <InteractiveSectionTitle 
                  children="Omega (ω) Sensitivity" 
                  subtitle="Sharpe ratio as omega varies from 0.05 to 0.60" 
                  onEdit={(newTitle) => console.log('Omega sensitivity section renamed to:', newTitle)}
                  editable={true}
                />
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={Array.from({length: 25}, (_, i) => {
                    const omegaVal = 0.05 + i * 0.022;
                    const result = runQSWOptimization(data, omegaVal, evolutionTime, maxWeight, turnoverLimit, evolutionMethod);
                    return { omega: omegaVal.toFixed(2), sharpe: result.sharpe, return: result.portReturn * 100, vol: result.portVol * 100 };
                  })} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
                    <defs>
                      <linearGradient id="omegaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={activeTheme.accent} stopOpacity={0.3} />
                        <stop offset="100%" stopColor={activeTheme.accent} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={activeTheme.border} />
                    <XAxis dataKey="omega" stroke={activeTheme.textDim} tick={{ fontSize: 10, fill: activeTheme.textDim }} label={{ value: "Omega (ω)", position: "bottom", fill: activeTheme.textDim, fontSize: 11 }} />
                    <YAxis stroke={activeTheme.textDim} tick={{ fontSize: 10, fill: activeTheme.textDim }} />
                    <Tooltip content={<CustomTooltip />} />
                    {typeof omega === 'number' && <ReferenceLine x={omega.toFixed(2)} stroke={activeTheme.accent} strokeDasharray="3 3" label={{ value: "Current", fill: activeTheme.accent, fontSize: 10 }} />}
                    <Area type="monotone" dataKey="sharpe" stroke={activeTheme.accent} fill="url(#omegaGrad)" strokeWidth={2} name="Sharpe" />
                  </AreaChart>
                </ResponsiveContainer>
                <div style={{ display: "flex", justifyContent: "center", gap: 4, marginTop: 8 }}>
                  <div style={{ background: `${activeTheme.green}20`, border: `1px solid ${activeTheme.green}40`, borderRadius: 4, padding: "2px 8px", fontSize: 10, color: activeTheme.green }}>
                    Chang optimal range: 0.20 - 0.40
                  </div>
                </div>
              </div>

              {/* Parameter Interaction */}
              <div style={{ background: activeTheme.surface, border: `1px solid ${activeTheme.border}`, borderRadius: 10, padding: 20, gridColumn: "1 / -1" }}>
                <InteractiveSectionTitle 
                  children="Parameter Impact Analysis" 
                  subtitle="How different parameters affect performance across methods" 
                  onEdit={(newTitle) => console.log('Parameter impact section renamed to:', newTitle)}
                  editable={true}
                />
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={[
                    { param: "Evolution Time", continuous: runQSWOptimization(data, omega, evolutionTime, maxWeight, turnoverLimit, 'continuous').sharpe,
                      discrete: runQSWOptimization(data, omega, evolutionTime, maxWeight, turnoverLimit, 'discrete').sharpe,
                      decoherent: runQSWOptimization(data, omega, evolutionTime, maxWeight, turnoverLimit, 'decoherent').sharpe,
                      annealing: runQuantumAnnealingOptimization(data, maxWeight).sharpe },
                    { param: "Max Weight", continuous: runQSWOptimization(data, omega, evolutionTime, 0.05, turnoverLimit, 'continuous').sharpe,
                      discrete: runQSWOptimization(data, omega, evolutionTime, 0.05, turnoverLimit, 'discrete').sharpe,
                      decoherent: runQSWOptimization(data, omega, evolutionTime, 0.05, turnoverLimit, 'decoherent').sharpe,
                      annealing: runQuantumAnnealingOptimization(data, 0.05).sharpe },
                    { param: "Omega", continuous: runQSWOptimization(data, 0.1, evolutionTime, maxWeight, turnoverLimit, 'continuous').sharpe,
                      discrete: runQSWOptimization(data, 0.1, evolutionTime, maxWeight, turnoverLimit, 'discrete').sharpe,
                      decoherent: runQSWOptimization(data, 0.1, evolutionTime, maxWeight, turnoverLimit, 'decoherent').sharpe,
                      annealing: runQuantumAnnealingOptimization(data, maxWeight).sharpe }
                  ]} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={activeTheme.border} />
                    <XAxis dataKey="param" stroke={activeTheme.textDim} tick={{ fontSize: 11, fill: activeTheme.textMuted }} />
                    <YAxis stroke={activeTheme.textDim} tick={{ fontSize: 10, fill: activeTheme.textDim }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="continuous" name="Continuous" fill={benchmarkColors["QSW"]} radius={[2, 2, 0, 0]} />
                    <Bar dataKey="discrete" name="Discrete" fill={benchmarkColors["QSW-Discrete"]} radius={[2, 2, 0, 0]} />
                    <Bar dataKey="decoherent" name="Decoherent" fill={benchmarkColors["QSW-Decoherent"]} radius={[2, 2, 0, 0]} />
                    <Bar dataKey="annealing" name="Annealing" fill={benchmarkColors["Quantum Annealing"]} radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
    </DashboardThemeContext.Provider>
  );
}

// Custom tooltip component
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: colors.surfaceLight, border: `1px solid ${colors.borderLight}`, borderRadius: 6, padding: "8px 12px", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>
      <div style={{ color: colors.textMuted, marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, display: "flex", gap: 8, justifyContent: "space-between" }}>
          <span>{p.name || p.dataKey}</span>
          <span style={{ fontWeight: 600 }}>{typeof p.value === 'number' ? p.value.toFixed(2) : p.value}</span>
        </div>
      ))}
    </div>
  );
}