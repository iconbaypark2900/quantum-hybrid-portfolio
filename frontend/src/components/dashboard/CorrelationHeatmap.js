import React, { useContext } from "react";
import { DashboardThemeContext } from "../../theme";
import SectionTitle from "./SectionTitle";

function CorrelationHeatmap({ apiResult, simData }) {
  const colors = useContext(DashboardThemeContext);
  let correlationMatrix, assetNames;

  if (apiResult?.correlation_matrix) {
    correlationMatrix = apiResult.correlation_matrix;
    assetNames = (apiResult.assets || []).map(a => a.name);
  } else if (simData?.corr && simData?.assets) {
    correlationMatrix = simData.corr;
    assetNames = simData.assets.map(a => a.name);
  } else {
    return null;
  }

  return (
    <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
      <SectionTitle subtitle="Correlation between portfolio assets" info="Pairwise correlation (-1 to 1). High positive = assets move together; negative = diversification benefit.">Correlation Heatmap</SectionTitle>
      <div style={{ overflowX: "auto" }} role="img" aria-label="Correlation heatmap of portfolio assets">
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}>
          <thead>
            <tr>
              <th style={{ padding: "4px", border: `1px solid ${colors.borderLight}` }}></th>
              {assetNames.slice(0, 10).map((name, i) => (
                <th key={`header-${i}`} style={{ padding: "4px", border: `1px solid ${colors.borderLight}`, transform: "translateX(-10px) rotate(-45deg)", whiteSpace: "nowrap" }}>
                  <div style={{ transform: "rotate(45deg)", width: "20px" }}>{name.substring(0, 4)}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {correlationMatrix.slice(0, 10).map((row, i) => (
              <tr key={`row-${i}`}>
                <td style={{ padding: "4px", border: `1px solid ${colors.borderLight}`, textAlign: "right", fontSize: 9 }}>{assetNames[i]?.substring(0, 4)}</td>
                {row.slice(0, 10).map((value, j) => {
                  const intensity = Math.abs(value);
                  const isPositive = value >= 0;
                  const cellColor = isPositive
                    ? `rgba(30, 136, 229, ${intensity})`
                    : `rgba(239, 68, 68, ${intensity})`;
                  return (
                    <td key={`cell-${i}-${j}`} style={{ padding: "4px", border: `1px solid ${colors.borderLight}`, backgroundColor: cellColor, color: intensity > 0.5 ? "white" : colors.text, textAlign: "center" }} title={`Correlation: ${value.toFixed(3)}`}>
                      {value.toFixed(2)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default React.memo(CorrelationHeatmap);
