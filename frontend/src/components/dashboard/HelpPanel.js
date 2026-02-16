import React, { useContext, useState } from "react";
import { FaTimes, FaChevronDown, FaChevronRight } from "react-icons/fa";
import { DashboardThemeContext } from "../../theme";

function HelpSection({ title, children, defaultOpen = false }) {
  const colors = useContext(DashboardThemeContext);
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ marginBottom: 8, border: `1px solid ${colors.border}`, borderRadius: 8, overflow: "hidden" }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: "100%",
          padding: "12px 14px",
          background: colors.surfaceLight,
          border: "none",
          color: colors.text,
          fontSize: 13,
          fontWeight: 600,
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontFamily: "'Space Grotesk', sans-serif",
        }}
      >
        {open ? <FaChevronDown size={12} /> : <FaChevronRight size={12} />}
        {title}
      </button>
      {open && (
        <div style={{ padding: "12px 14px", fontSize: 12, color: colors.textMuted, lineHeight: 1.6 }}>
          {children}
        </div>
      )}
    </div>
  );
}

function HelpPanel({ onClose }) {
  const colors = useContext(DashboardThemeContext);
  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.4)",
          zIndex: 999,
          cursor: "pointer",
        }}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-label="Help and documentation"
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          width: "min(420px, 100vw)",
          height: "100vh",
          background: colors.surface,
          borderLeft: `1px solid ${colors.border}`,
          zIndex: 1000,
          overflowY: "auto",
          boxShadow: "-4px 0 24px rgba(0,0,0,0.3)",
        }}
      >
        <div style={{ padding: 20, borderBottom: `1px solid ${colors.border}`, display: "flex", alignItems: "center", justifyContent: "space-between", background: colors.bg }}>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: colors.text }}>Help & Documentation</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              padding: 8,
              background: "transparent",
              border: "none",
              color: colors.textMuted,
              cursor: "pointer",
              borderRadius: 6,
            }}
          >
            <FaTimes size={18} />
          </button>
        </div>
        <div style={{ padding: 16 }}>
          <p style={{ fontSize: 12, color: colors.textMuted, marginBottom: 16, lineHeight: 1.5 }}>
            Quantum Portfolio Lab uses QSW-inspired optimization with HRP and Ledoit&ndash;Wolf covariance. Hover over info icons for quick tips.
          </p>

          <HelpSection title="Getting Started" defaultOpen>
            <p style={{ margin: "0 0 8px 0" }}>1. Choose <strong>Simulation</strong> or <strong>Live API</strong> in the header.</p>
            <p style={{ margin: "0 0 8px 0" }}>2. Set tickers and dates (Live) or regime and seed (Simulation).</p>
            <p style={{ margin: "0 0 8px 0" }}>3. Click <strong>Run Optimization</strong> (Live) or let Simulation run automatically.</p>
            <p style={{ margin: 0 }}>4. Use the tabs to explore Holdings, Performance, Risk, and more.</p>
          </HelpSection>

          <HelpSection title="Data Modes">
            <p style={{ margin: "0 0 8px 0" }}><strong>Simulation</strong> — Synthetic market data from regime parameters. No API needed. Good for experimenting.</p>
            <p style={{ margin: 0 }}><strong>Live API</strong> — Real market data from the backend. Requires API on port 5000. Use for real portfolios.</p>
          </HelpSection>

          <HelpSection title="Tabs Overview">
            <p style={{ margin: "0 0 6px 0" }}><strong>Holdings</strong> — Weights, sector breakdown, trade blotter, benchmark comparison.</p>
            <p style={{ margin: "0 0 6px 0" }}><strong>Performance</strong> — Backtest, drawdown chart, equity curve, strategy comparison.</p>
            <p style={{ margin: "0 0 6px 0" }}><strong>Risk</strong> — Correlation heatmap, efficient frontier, VaR, sector exposure, stress tests.</p>
            <p style={{ margin: "0 0 6px 0" }}><strong>Analysis</strong> — What-if weight adjuster, regime comparison.</p>
            <p style={{ margin: "0 0 6px 0" }}><strong>Sensitivity</strong> — Omega, max weight, evolution time sensitivity charts.</p>
            <p style={{ margin: 0 }}><strong>Scenarios</strong> — Batch backtest index/ETF scenarios; Load applies one to the dashboard.</p>
          </HelpSection>

          <HelpSection title="Left Panel Controls">
            <p style={{ margin: "0 0 6px 0" }}><strong>Omega</strong> — Quantum vs classical coupling. Higher = more quantum influence.</p>
            <p style={{ margin: "0 0 6px 0" }}><strong>Evolution Time</strong> — Diffusion steps. Higher = more smoothing.</p>
            <p style={{ margin: "0 0 6px 0" }}><strong>Regime</strong> — Normal, Bull, Bear, Volatile (simulation only).</p>
            <p style={{ margin: "0 0 6px 0" }}><strong>Objective</strong> — Max Sharpe, Min Variance, Risk Parity, HRP, Target Return.</p>
            <p style={{ margin: 0 }}><strong>Constraints</strong> — Max weight per position, turnover limit, universe size.</p>
          </HelpSection>

          <HelpSection title="Metric Cards">
            <p style={{ margin: "0 0 6px 0" }}>Toggle <strong>Optimization</strong> vs <strong>Backtest</strong> when a backtest exists to compare results.</p>
            <p style={{ margin: 0 }}>Sharpe, Return, Volatility, Active Positions, VaR. Delta shows change vs benchmark.</p>
          </HelpSection>

          <HelpSection title="Tips">
            <p style={{ margin: "0 0 6px 0" }}>• Hover over <strong>info icons</strong> for explanations.</p>
            <p style={{ margin: "0 0 6px 0" }}>• Use <strong>Export</strong> to download portfolio data as JSON.</p>
            <p style={{ margin: "0 0 6px 0" }}>• In Scenarios, use <strong>Load</strong> to apply a scenario to the main view.</p>
            <p style={{ margin: 0 }}>• Theme toggle switches dark/light mode.</p>
          </HelpSection>

          <div style={{ marginTop: 20, padding: 12, background: colors.surfaceLight, borderRadius: 8, border: `1px solid ${colors.border}`, fontSize: 11, color: colors.textDim }}>
            <strong style={{ color: colors.text }}>Full documentation</strong> — See <code style={{ background: colors.bg, padding: "2px 6px", borderRadius: 4 }}>docs/</code> in the project for API reference, architecture, and detailed guides.
          </div>
        </div>
      </div>
    </>
  );
}

export default React.memo(HelpPanel);
