import { createContext } from "react";

export const darkTheme = {
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
  highContrastText: "#FFFFFF",
  highContrastBg: "#000000",
  focusOutline: "#FFD700",
  focusOutlineWidth: "3px",
};

export const lightTheme = {
  bg: "#F8FAFC",
  surface: "#FFFFFF",
  surfaceLight: "#F1F5F9",
  border: "#E2E8F0",
  borderLight: "#CBD5E1",
  text: "#1E293B",
  textMuted: "#475569",
  textDim: "#94A3B8",
  accent: "#2563EB",
  accentGlow: "rgba(37,99,235,0.10)",
  green: "#059669",
  greenDim: "rgba(5,150,105,0.10)",
  red: "#DC2626",
  redDim: "rgba(220,38,38,0.10)",
  orange: "#D97706",
  purple: "#7C3AED",
  cyan: "#0891B2",
  pink: "#DB2777",
  highContrastText: "#000000",
  highContrastBg: "#FFFFFF",
  focusOutline: "#2563EB",
  focusOutlineWidth: "3px",
};

export const chartColors = [
  "#3B82F6", "#10B981", "#F59E0B", "#EF4444",
  "#8B5CF6", "#06B6D4", "#EC4899", "#F97316",
];

export const benchmarkColors = {
  QSW: "#3B82F6",
  "QSW-Discrete": "#8B5CF6",
  "QSW-Decoherent": "#06B6D4",
  "QSW-Adiabatic": "#EC4899",
  "QSW-Variational": "#F97316",
  "Quantum Annealing": "#EC4899",
  "Equal Weight": "#8B9DC3",
  "Min Variance": "#10B981",
  "Risk Parity": "#F59E0B",
  "Max Sharpe": "#8B5CF6",
  "HRP": "#14B8A6",
};

export const DashboardThemeContext = createContext(darkTheme);

export function useTheme() {
  const ctx = require("react").useContext(DashboardThemeContext);
  return ctx || darkTheme;
}

export const CHART_COLORS = [
  "#3B82F6", "#10B981", "#F59E0B", "#EF4444",
  "#8B5CF6", "#06B6D4", "#EC4899", "#F97316",
];

export const STRATEGY_COLORS = {
  markowitz: "#3B82F6",
  min_variance: "#10B981",
  hrp: "#F59E0B",
  equal_weight: "#8B9DC3",
  qubo_sa: "#8B5CF6",
  vqe: "#06B6D4",
  hybrid: "#EC4899",
};

export const FONT = {
  sans: "'Inter', 'Space Grotesk', system-ui, sans-serif",
  mono: "'JetBrains Mono', 'Fira Mono', monospace",
};
