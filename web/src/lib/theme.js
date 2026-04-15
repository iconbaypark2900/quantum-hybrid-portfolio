import { createContext, useContext } from "react";

/** Neutrals aligned with globals.css `.dark` (warm charcoal, same role as light mode stone ramp).
 *  Upgraded dark mode palette: richer depth, softer borders, more vibrant accents. */
export const darkTheme = {
  bg: "#0b0a08",
  surface: "#141210",
  surfaceLight: "#1e1c19",
  surfaceElevated: "#25221f",
  border: "#3a3733",
  borderLight: "#4a4743",
  borderSubtle: "rgba(74,71,67,0.5)",
  text: "#f0ede8",
  textMuted: "#b5b0a8",
  textDim: "#8a847c",
  textFaint: "#5c5750",
  accent: "#00e6b8",
  accentDim: "rgba(0,230,184,0.14)",
  accentWarm: "#fbbf24",
  accentWarmDim: "rgba(251,191,36,0.14)",
  green: "#34d399",
  greenDim: "rgba(52,211,153,0.14)",
  red: "#f87171",
  redDim: "rgba(248,113,113,0.14)",
  orange: "#fbbf24",
  purple: "#a78bfa",
  cyan: "#22d3ee",
  pink: "#f472b6",
  shadow: "0 2px 8px rgba(0,0,0,0.35)",
  shadowLg: "0 4px 16px rgba(0,0,0,0.45)",
  glow: "0 0 20px rgba(0,230,184,0.15)",
};

/** Neutrals aligned with globals.css `:root` / `.light` (warm off-white ramp). */
export const lightTheme = {
  bg: "#faf8f5",
  surface: "#f4f2ee",
  surfaceLight: "#ebe8e3",
  surfaceElevated: "#ffffff",
  border: "#dbd7d0",
  borderLight: "#cfccc4",
  borderSubtle: "rgba(219,215,208,0.6)",
  text: "#1a1c20",
  textMuted: "#44474e",
  textDim: "#74777e",
  textFaint: "#a8abb2",
  accent: "#059669",
  accentDim: "rgba(5,150,105,0.10)",
  accentWarm: "#d97706",
  accentWarmDim: "rgba(217,119,6,0.10)",
  green: "#059669",
  greenDim: "rgba(5,150,105,0.10)",
  red: "#dc2626",
  redDim: "rgba(220,38,38,0.10)",
  orange: "#d97706",
  purple: "#7c3aed",
  cyan: "#0891b2",
  pink: "#db2777",
  shadow: "0 1px 3px rgba(0,0,0,0.08)",
  shadowLg: "0 4px 12px rgba(0,0,0,0.12)",
  glow: "none",
};

export const CHART_COLORS = [
  "#00e6b8", "#a78bfa", "#fbbf24", "#f87171", "#34d399", "#94a3b8",
  "#22d3ee", "#f472b6",
];

export const STRATEGY_COLORS = {
  Hybrid: "#00e6b8",
  Markowitz: "#a78bfa",
  HRP: "#34d399",
  "QUBO-SA": "#fbbf24",
  VQE: "#22d3ee",
  "Equal Weight": "#94a3b8",
  "Min Variance": "#34d399",
  "Risk Parity": "#f472b6",
  "Max Sharpe": "#a78bfa",
};

export const FONT = {
  mono: "'JetBrains Mono', 'Fira Code', monospace",
  sans: "'IBM Plex Sans', 'DM Sans', system-ui, sans-serif",
};

export const DashboardThemeContext = createContext(darkTheme);

export function useTheme() {
  return useContext(DashboardThemeContext);
}

export function themeForResolved(resolved) {
  return resolved === "light" ? lightTheme : darkTheme;
}
