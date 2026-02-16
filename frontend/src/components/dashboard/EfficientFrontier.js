import React, { useState, useContext } from "react";
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { getEfficientFrontier } from "../../services/api";
import { DashboardThemeContext, benchmarkColors } from "../../theme";
import SectionTitle from "./SectionTitle";
import CustomTooltip from "./CustomTooltip";

function EfficientFrontier({ tickers, startDate, endDate, qswResult, apiResult }) {
  const colors = useContext(DashboardThemeContext);
  const [frontierData, setFrontierData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchFrontier = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getEfficientFrontier(tickers, startDate, endDate, 20);
      setFrontierData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
      <SectionTitle subtitle="Risk-return efficient frontier with current portfolio" info="Optimal risk-return combinations. Your portfolio is plotted for comparison.">Efficient Frontier</SectionTitle>
      <button onClick={fetchFrontier} disabled={loading}
        style={{ width: "100%", padding: "10px", backgroundColor: colors.accent, color: "white", border: "none", borderRadius: 6, cursor: loading ? "not-allowed" : "pointer", marginBottom: 16 }}>
        {loading ? "Calculating Frontier..." : "Show Efficient Frontier"}
      </button>
      {error && <div style={{ color: colors.red, padding: "10px", background: colors.redDim, borderRadius: 6, marginBottom: 16 }}>Error: {error}</div>}
      {frontierData && (
        <div style={{ height: 400 }} role="img" aria-label="Efficient frontier scatter plot">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
              <XAxis type="number" dataKey="volatility" name="Volatility" label={{ value: 'Volatility (%)', position: 'bottom', fill: colors.textMuted, fontSize: 11 }} stroke={colors.textDim} tick={{ fontSize: 10 }} />
              <YAxis type="number" dataKey="target_return" name="Return" label={{ value: 'Return (%)', angle: -90, position: 'insideLeft', fill: colors.textMuted, fontSize: 11 }} stroke={colors.textDim} tick={{ fontSize: 10 }} />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} content={<CustomTooltip />} />
              <Legend />
              <Scatter name="Efficient Frontier" data={frontierData.frontier_points} fill={colors.accent} line={{ stroke: colors.accent, strokeWidth: 2 }} shape="cross" />
              {qswResult && (
                <Scatter name="Current Portfolio" data={[{ volatility: (qswResult.volatility || qswResult.portVol || 0) * 100, target_return: (qswResult.expected_return || qswResult.portReturn || 0) * 100 }]} fill={colors.green} shape="star" size={100} />
              )}
              {apiResult?.benchmarks && (
                <>
                  {apiResult.benchmarks.equal_weight && (
                    <Scatter name="Equal Weight" data={[{ volatility: apiResult.benchmarks.equal_weight.volatility * 100, target_return: apiResult.benchmarks.equal_weight.expected_return * 100 }]} fill={colors.textMuted} shape="circle" size={64} />
                  )}
                  {apiResult.benchmarks.min_variance && (
                    <Scatter name="Min Variance" data={[{ volatility: apiResult.benchmarks.min_variance.volatility * 100, target_return: apiResult.benchmarks.min_variance.expected_return * 100 }]} fill={benchmarkColors["Min Variance"]} shape="triangle" size={64} />
                  )}
                  {apiResult.benchmarks.risk_parity && (
                    <Scatter name="Risk Parity" data={[{ volatility: apiResult.benchmarks.risk_parity.volatility * 100, target_return: apiResult.benchmarks.risk_parity.expected_return * 100 }]} fill={benchmarkColors["Risk Parity"]} shape="diamond" size={64} />
                  )}
                  {apiResult.benchmarks.hrp && (
                    <Scatter name="HRP" data={[{ volatility: apiResult.benchmarks.hrp.volatility * 100, target_return: apiResult.benchmarks.hrp.expected_return * 100 }]} fill={benchmarkColors["HRP"]} shape="square" size={64} />
                  )}
                </>
              )}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export default React.memo(EfficientFrontier);
