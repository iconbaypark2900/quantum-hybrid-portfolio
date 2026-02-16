import React, { useContext } from "react";
import { DashboardThemeContext } from "../../theme";
import SectionTitle from "./SectionTitle";

function BenchmarkComparison({ apiResult, simData, simBenchmarks, simQswWeights }) {
  const colors = useContext(DashboardThemeContext);
  let qswWeights, assetNames, ewWeights, mvWeights, rpWeights, hrpWeights;

  if (apiResult && apiResult.benchmarks) {
    qswWeights = apiResult.qsw_result?.weights || [];
    assetNames = (apiResult.assets || []).map(a => a.name);
    ewWeights = apiResult.benchmarks.equal_weight?.weights || [];
    mvWeights = apiResult.benchmarks.min_variance?.weights || [];
    rpWeights = apiResult.benchmarks.risk_parity?.weights || [];
    hrpWeights = apiResult.benchmarks.hrp?.weights || [];
  } else if (simData && simBenchmarks && simQswWeights) {
    qswWeights = simQswWeights;
    assetNames = simData.assets.map(a => a.name);
    ewWeights = simBenchmarks.equalWeight?.weights || [];
    mvWeights = simBenchmarks.minVariance?.weights || [];
    rpWeights = simBenchmarks.riskParity?.weights || [];
    hrpWeights = simBenchmarks.hrp?.weights || [];
  } else {
    return null;
  }

  const topAssets = [...qswWeights]
    .map((weight, index) => ({ index, weight }))
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 10)
    .map(item => ({ ...item, name: assetNames[item.index] || `Asset ${item.index}` }));

  return (
    <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
      <SectionTitle subtitle="Top holdings comparison across different portfolio strategies" info="QSW vs Equal Weight, Min Variance, Risk Parity, HRP. Shows weight differences.">Benchmark Weight Comparison</SectionTitle>
      <div style={{ maxHeight: 400, overflowY: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${colors.border}` }}>
              <th style={{ textAlign: "left", padding: "8px", color: colors.textMuted }}>Asset</th>
              <th style={{ textAlign: "right", padding: "8px", color: colors.textMuted }}>QSW</th>
              <th style={{ textAlign: "right", padding: "8px", color: colors.textMuted }}>EW</th>
              <th style={{ textAlign: "right", padding: "8px", color: colors.textMuted }}>MV</th>
              <th style={{ textAlign: "right", padding: "8px", color: colors.textMuted }}>RP</th>
              <th style={{ textAlign: "right", padding: "8px", color: colors.textMuted }}>HRP</th>
            </tr>
          </thead>
          <tbody>
            {topAssets.map((asset, i) => (
              <tr key={asset.name || i} style={{ borderBottom: `1px solid ${colors.borderLight}` }}>
                <td style={{ padding: "8px", color: colors.text }}>{asset.name}</td>
                <td style={{ padding: "8px", color: colors.accent, textAlign: "right" }}>{(qswWeights[asset.index] * 100).toFixed(2)}%</td>
                <td style={{ padding: "8px", color: colors.textMuted, textAlign: "right" }}>{ewWeights[asset.index] != null ? (ewWeights[asset.index] * 100).toFixed(2) + "%" : "N/A"}</td>
                <td style={{ padding: "8px", color: colors.textMuted, textAlign: "right" }}>{mvWeights[asset.index] != null ? (mvWeights[asset.index] * 100).toFixed(2) + "%" : "N/A"}</td>
                <td style={{ padding: "8px", color: colors.textMuted, textAlign: "right" }}>{rpWeights[asset.index] != null ? (rpWeights[asset.index] * 100).toFixed(2) + "%" : "N/A"}</td>
                <td style={{ padding: "8px", color: colors.textMuted, textAlign: "right" }}>{hrpWeights[asset.index] != null ? (hrpWeights[asset.index] * 100).toFixed(2) + "%" : "N/A"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default React.memo(BenchmarkComparison);
