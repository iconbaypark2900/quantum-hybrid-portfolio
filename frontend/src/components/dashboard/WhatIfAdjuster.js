import React, { useState, useEffect, useContext } from "react";
import { DashboardThemeContext } from "../../theme";
import SectionTitle from "./SectionTitle";

function WhatIfAdjuster({ holdings, onWeightsChanged }) {
  const colors = useContext(DashboardThemeContext);
  const [localWeights, setLocalWeights] = useState({});

  useEffect(() => {
    if (holdings && holdings.length > 0) {
      const initialWeights = {};
      holdings.slice(0, 8).forEach(holding => { initialWeights[holding.name] = holding.weight * 100; });
      setLocalWeights(initialWeights);
    }
  }, [holdings]);

  const handleWeightChange = (assetName, newWeight) => {
    const updatedWeights = { ...localWeights, [assetName]: parseFloat(newWeight) };
    setLocalWeights(updatedWeights);
    const totalWeight = Object.values(updatedWeights).reduce((sum, w) => sum + w, 0);
    if (totalWeight > 0 && onWeightsChanged) {
      const normalizedWeights = holdings.map(holding => {
        if (updatedWeights.hasOwnProperty(holding.name)) return updatedWeights[holding.name] / 100;
        const remainingWeight = 100 - Object.values(updatedWeights).reduce((sum, w) => sum + w, 0);
        const nonAdjustedCount = holdings.length - Object.keys(updatedWeights).length;
        return (remainingWeight / nonAdjustedCount) / 100;
      });
      onWeightsChanged(normalizedWeights);
    }
  };

  return (
    <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
      <SectionTitle subtitle="Adjust weights of top holdings to see impact on metrics" info="Sliders let you tweak allocations; metrics below update to show Sharpe, return, vol impact.">What-If Weight Adjuster</SectionTitle>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 16 }}>
        {holdings.slice(0, 8).map((holding, i) => (
          <div key={holding.name || i} style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 12, color: colors.textMuted, marginBottom: 4 }}>{holding.name} ({(holding.weight * 100).toFixed(1)}%)</div>
            <input type="range" min="0" max="30" step="0.1" value={localWeights[holding.name] || (holding.weight * 100)}
              onChange={(e) => handleWeightChange(holding.name, e.target.value)}
              aria-label={`Weight for ${holding.name}`}
              style={{ width: "100%", height: 8, appearance: "none", background: `linear-gradient(to right, ${colors.accent} ${(localWeights[holding.name] || (holding.weight * 100))}%, ${colors.border} ${(localWeights[holding.name] || (holding.weight * 100))}%)`, borderRadius: 4, outline: "none", cursor: "pointer" }} />
            <div style={{ textAlign: "right", fontSize: 11, color: colors.accent, marginTop: 4 }}>{(localWeights[holding.name] || (holding.weight * 100)).toFixed(1)}%</div>
          </div>
        ))}
      </div>
      <button onClick={() => {
        const originalWeights = {};
        holdings.slice(0, 8).forEach(holding => { originalWeights[holding.name] = holding.weight * 100; });
        setLocalWeights(originalWeights);
        if (onWeightsChanged) onWeightsChanged(holdings.map(h => h.weight));
      }} style={{ marginTop: 16, padding: "8px 16px", backgroundColor: colors.surfaceLight, color: colors.text, border: `1px solid ${colors.border}`, borderRadius: 6, cursor: "pointer" }}>
        Reset to Optimized
      </button>
    </div>
  );
}

export default React.memo(WhatIfAdjuster);
