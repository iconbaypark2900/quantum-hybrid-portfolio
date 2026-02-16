import React from 'react';
import { FaCaretUp, FaCaretDown, FaDotCircle, FaChartLine } from 'react-icons/fa';

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
};

export const Slider = ({ label, value, onChange, min, max, step, unit = "", info }) => {
  const percentage = ((value - min) / (max - min)) * 100;
  
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={{ fontSize: 12, color: colors.textMuted, letterSpacing: "0.05em", textTransform: "uppercase", fontFamily: "'JetBrains Mono', monospace" }}>{label}</span>
        <span style={{ fontSize: 13, color: colors.accent, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>
          {typeof value === 'number' ? value.toFixed(step < 1 ? 2 : 0) : value}
          {unit}
        </span>
      </div>
      <input 
        type="range" 
        min={min} 
        max={max} 
        step={step} 
        value={value} 
        onChange={e => onChange(parseFloat(e.target.value))}
        style={{ 
          width: "100%", 
          height: 4, 
          appearance: "none", 
          background: `linear-gradient(to right, ${colors.accent} ${percentage}%, ${colors.border} ${percentage}%)`,
          borderRadius: 2, 
          outline: "none", 
          cursor: "pointer",
          padding: 0 
        }} 
      />
      {info && <div style={{ fontSize: 10, color: colors.textDim, marginTop: 4, fontStyle: "italic" }}>{info}</div>}
    </div>
  );
};

export const MetricCard = ({ label, value, unit, delta, description, color = colors.accent }) => {
  return (
    <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 8, padding: "14px 16px", flex: 1, minWidth: 140 }}>
      <div style={{ fontSize: 10, color: colors.textDim, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>{label}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
        <span style={{ fontSize: 24, fontWeight: 700, color, fontFamily: "'JetBrains Mono', monospace" }}>{value}</span>
        {unit && <span style={{ fontSize: 12, color: colors.textMuted }}>{unit}</span>}
      </div>
      {delta !== undefined && (
        <div style={{ fontSize: 11, color: delta >= 0 ? colors.green : colors.red, marginTop: 4, fontFamily: "'JetBrains Mono', monospace" }}>
          {delta >= 0 ? <FaCaretUp size={10} style={{ display: "inline", verticalAlign: "middle" }} /> : <FaCaretDown size={10} style={{ display: "inline", verticalAlign: "middle" }} />} {Math.abs(delta).toFixed(1)}% vs benchmark
        </div>
      )}
      {description && <div style={{ fontSize: 10, color: colors.textDim, marginTop: 4 }}>{description}</div>}
    </div>
  );
};

export const TabButton = ({ active, onClick, children, icon }) => {
  return (
    <button 
      onClick={onClick} 
      style={{
        padding: "10px 18px", 
        background: active ? colors.accentGlow : "transparent",
        border: `1px solid ${active ? colors.accent : "transparent"}`, 
        borderRadius: 6,
        color: active ? colors.accent : colors.textMuted, 
        fontSize: 13, 
        fontWeight: active ? 600 : 400,
        cursor: "pointer", 
        transition: "all 0.2s", 
        display: "flex", 
        alignItems: "center", 
        gap: 6,
        fontFamily: "'JetBrains Mono', monospace", 
        letterSpacing: "0.02em",
      }}
    >
      {icon && <span style={{ fontSize: 15 }}>{icon}</span>}
      {children}
    </button>
  );
};

export const SectionTitle = ({ children, subtitle }) => {
  return (
    <div style={{ marginBottom: 16 }}>
      <h3 style={{ fontSize: 15, fontWeight: 700, color: colors.text, margin: 0, fontFamily: "'Space Grotesk', sans-serif", letterSpacing: "-0.01em" }}>{children}</h3>
      {subtitle && <p style={{ fontSize: 11, color: colors.textDim, margin: "4px 0 0 0" }}>{subtitle}</p>}
    </div>
  );
};

export const RegimeSelector = ({ value, onChange }) => {
  const regimes = [
    { key: "normal", label: "Normal", icon: <FaDotCircle size={14} />, color: colors.accent },
    { key: "bull", label: "Bull", icon: <FaCaretUp size={14} />, color: colors.green },
    { key: "bear", label: "Bear", icon: <FaCaretDown size={14} />, color: colors.red },
    { key: "volatile", label: "Volatile", icon: <FaChartLine size={14} />, color: colors.orange },
  ];
  
  return (
    <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
      {regimes.map(r => (
        <button 
          key={r.key} 
          onClick={() => onChange(r.key)} 
          style={{
            flex: 1, 
            padding: "8px 4px", 
            background: value === r.key ? `${r.color}18` : "transparent",
            border: `1px solid ${value === r.key ? r.color : colors.border}`, 
            borderRadius: 6,
            color: value === r.key ? r.color : colors.textDim, 
            fontSize: 11, 
            cursor: "pointer",
            fontFamily: "'JetBrains Mono', monospace", 
            transition: "all 0.2s", 
            textAlign: "center"
          }}
        >
          <div style={{ fontSize: 16 }}>{r.icon}</div>
          <div style={{ marginTop: 2 }}>{r.label}</div>
        </button>
      ))}
    </div>
  );
};