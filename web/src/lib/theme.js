import { createContext, useContext } from "react";

/** Neutrals aligned with globals.css `.dark` (warm charcoal, same role as light mode stone ramp). */
export const darkTheme = {
  bg: "#0f0e0c",
  surface: "#171514",
  surfaceLight: "#262320",
  border: "#4a4743",
  borderLight: "#5c5756",
  text: "#ebe8e4",
  textMuted: "#a8a39c",
  textDim: "#7f7a73",
  accent: "#00d4aa",
  accentDim: "rgba(0,212,170,0.12)",
  accentWarm: "#f59e0b",
  accentWarmDim: "rgba(245,158,11,0.12)",
  green: "#22c55e",
  greenDim: "rgba(34,197,94,0.12)",
  red: "#ef4444",
  redDim: "rgba(239,68,68,0.12)",
  orange: "#f59e0b",
  purple: "#7c6bff",
  cyan: "#06b6d4",
  pink: "#ec4899",
};

/** Neutrals aligned with globals.css `:root` / `.light` (warm off-white ramp). */
export const lightTheme = {
  bg: "#faf8f5",
  surface: "#f4f2ee",
  surfaceLight: "#ebe8e3",
  border: "#dbd7d0",
  borderLight: "#cfccc4",
  text: "#1a1c20",
  textMuted: "#44474e",
  textDim: "#74777e",
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
};

export const CHART_COLORS = [
  "#00d4aa", "#7c6bff", "#f59e0b", "#ef4444", "#22c55e", "#64748b",
  "#06b6d4", "#ec4899",
];

export const STRATEGY_COLORS = {
  Hybrid: "#00d4aa",
  Markowitz: "#7c6bff",
  HRP: "#22c55e",
  "QUBO-SA": "#f59e0b",
  VQE: "#06b6d4",
  "Equal Weight": "#64748b",
  "Min Variance": "#22c55e",
  "Risk Parity": "#ec4899",
  "Max Sharpe": "#7c6bff",
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
