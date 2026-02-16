import React, { useState, useContext } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { optimizePortfolio } from "../../services/api";
import { generateMarketData, runEnhancedQSWOptimization } from "../../lib/simulationEngine";
import { DashboardThemeContext } from "../../theme";
import SectionTitle from "./SectionTitle";
import CustomTooltip from "./CustomTooltip";

function RegimeComparison({ tickers, startDate, endDate, objective, strategyPreset, constraints, apiResult }) {
  const colors = useContext(DashboardThemeContext);
  const [regimeResults, setRegimeResults] = useState({});
  const [loading, setLoading] = useState({});
  const [completed, setCompleted] = useState([]);

  const runRegimeOptimization = async (regime) => {
    setLoading(prev => ({ ...prev, [regime]: true }));
    try {
      if (!apiResult) {
        const data = generateMarketData(tickers.length, 252, regime, 42, tickers);
        const result = runEnhancedQSWOptimization(data, 0.3, 10, 0.1, 0.2);
        setRegimeResults(prev => ({ ...prev, [regime]: result }));
      } else {
        const result = await optimizePortfolio({ tickers, startDate, endDate, regime, omega: 0.3, evolutionTime: 10, maxWeight: 0.1, turnoverLimit: 0.2, objective: objective || 'max_sharpe', strategyPreset, constraints });
        setRegimeResults(prev => ({ ...prev, [regime]: result.qsw_result }));
      }
      setCompleted(prev => [...prev, regime]);
    } catch (_) {
      // Silently handle
    } finally {
      setLoading(prev => ({ ...prev, [regime]: false }));
    }
  };

  const regimes = ['bull', 'bear', 'normal', 'volatile'];

  return (
    <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
      <SectionTitle subtitle="Portfolio performance across different market regimes" info="Run optimization under bull, bear, normal, volatile regimes to compare robustness.">Regime Comparison</SectionTitle>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {regimes.map(regime => (
          <button key={regime} onClick={() => runRegimeOptimization(regime)} disabled={loading[regime]}
            style={{ padding: "6px 12px", backgroundColor: completed.includes(regime) ? colors.green : colors.accent, color: "white", border: "none", borderRadius: 6, cursor: "pointer", opacity: loading[regime] ? 0.6 : 1 }}>
            {loading[regime] ? `Running ${regime}...` : `Run ${regime.charAt(0).toUpperCase() + regime.slice(1)}`}
          </button>
        ))}
      </div>
      {Object.keys(regimeResults).length > 0 && (
        <div style={{ height: 300 }} role="img" aria-label="Regime comparison bar chart">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={regimes.map(regime => {
              const r = regimeResults[regime];
              return { regime: regime.charAt(0).toUpperCase() + regime.slice(1), sharpe: r?.sharpe_ratio || r?.sharpe || 0, return: ((r?.expected_return || r?.portReturn || 0) * 100), vol: ((r?.volatility || r?.portVol || 0) * 100) };
            })} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
              <XAxis dataKey="regime" stroke={colors.textDim} />
              <YAxis stroke={colors.textDim} />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Bar dataKey="sharpe" name="Sharpe Ratio" fill={colors.accent} />
              <Bar dataKey="return" name="Return (%)" fill={colors.green} />
              <Bar dataKey="vol" name="Vol (%)" fill={colors.orange} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export default React.memo(RegimeComparison);
