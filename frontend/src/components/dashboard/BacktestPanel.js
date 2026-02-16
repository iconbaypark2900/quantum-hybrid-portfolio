import React, { useState, useContext } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { runBacktest as apiRunBacktest } from "../../services/api";
import { DashboardThemeContext } from "../../theme";
import SectionTitle from "./SectionTitle";
import CustomTooltip from "./CustomTooltip";

function normalizeBacktestResult(raw) {
  if (!raw) return raw;
  if ('total_return' in raw && 'equity_curve' in raw) return raw;
  const sm = raw.summary_metrics || {};
  const equityCurve = (raw.results || raw.equity_curve || []).map(pt => ({
    date: pt.date,
    portfolio_value: pt.portfolio_value ?? pt.cumulative_value ?? 0,
    portfolio_return: pt.portfolio_return ?? 0,
  }));
  return {
    total_return: sm.total_return ?? raw.total_return ?? 0,
    annual_return: sm.annual_return ?? raw.annual_return ?? 0,
    sharpe_ratio: sm.sharpe_ratio ?? raw.sharpe_ratio ?? 0,
    max_drawdown: sm.max_drawdown ?? raw.max_drawdown ?? 0,
    volatility: sm.volatility ?? raw.volatility ?? 0,
    equity_curve: equityCurve,
    parameters: raw.parameters,
    summary_metrics: sm,
  };
}

function BacktestPanel({ tickers, startDate, endDate, objective, targetReturn, strategyPreset, constraints, onBacktestComplete }) {
  const colors = useContext(DashboardThemeContext);
  const [backtestResult, setBacktestResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleRunBacktest = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { tickers, start_date: startDate, end_date: endDate, rebalance_frequency: 'monthly', objective, strategy_preset: strategyPreset, constraints };
      if (objective === 'target_return' && targetReturn != null) params.target_return = targetReturn;
      const raw = await apiRunBacktest(params);
      const normalized = normalizeBacktestResult(raw);
      setBacktestResult(normalized);
      if (onBacktestComplete) onBacktestComplete(normalized);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
      <SectionTitle subtitle="Run historical backtest to see real performance" info="Uses your tickers and date range to compute portfolio returns with monthly rebalancing.">Backtest Panel</SectionTitle>
      <button onClick={handleRunBacktest} disabled={loading}
        style={{ width: "100%", padding: "10px", backgroundColor: colors.accent, color: "white", border: "none", borderRadius: 6, cursor: loading ? "not-allowed" : "pointer", marginBottom: 16 }}>
        {loading ? "Running Backtest..." : "Run Backtest"}
      </button>
      {error && <div style={{ color: colors.red, padding: "10px", background: colors.redDim, borderRadius: 6, marginBottom: 16 }}>Error: {error}</div>}
      {backtestResult && (
        <div>
          <div style={{ display: "flex", gap: 16, marginBottom: 16, flexWrap: "wrap" }}>
            <div style={{ flex: 1, minWidth: 150 }}>
              <div style={{ fontSize: 12, color: colors.textMuted, marginBottom: 4 }}>Total Return</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: colors.green }}>{(backtestResult.total_return * 100).toFixed(2)}%</div>
            </div>
            <div style={{ flex: 1, minWidth: 150 }}>
              <div style={{ fontSize: 12, color: colors.textMuted, marginBottom: 4 }}>Annual Return</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: colors.accent }}>{(backtestResult.annual_return * 100).toFixed(2)}%</div>
            </div>
            <div style={{ flex: 1, minWidth: 150 }}>
              <div style={{ fontSize: 12, color: colors.textMuted, marginBottom: 4 }}>Sharpe Ratio</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: colors.purple }}>{backtestResult.sharpe_ratio.toFixed(3)}</div>
            </div>
            <div style={{ flex: 1, minWidth: 150 }}>
              <div style={{ fontSize: 12, color: colors.textMuted, marginBottom: 4 }}>Max Drawdown</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: colors.red }}>{(backtestResult.max_drawdown * 100).toFixed(2)}%</div>
            </div>
          </div>
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={backtestResult.equity_curve}>
                <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
                <XAxis dataKey="date" stroke={colors.textDim} tick={{ fontSize: 10 }} label={{ value: "Date", position: "bottom", fill: colors.textDim, fontSize: 11 }} />
                <YAxis stroke={colors.textDim} tick={{ fontSize: 10 }} label={{ value: "Portfolio Value ($)", angle: -90, position: "insideLeft", fill: colors.textDim, fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Line type="monotone" dataKey="portfolio_value" stroke={colors.accent} strokeWidth={2} dot={false} name="Portfolio Value" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}

export default React.memo(BacktestPanel);
