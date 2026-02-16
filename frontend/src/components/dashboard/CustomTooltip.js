import React, { useContext } from "react";
import { DashboardThemeContext } from "../../theme";

function CustomTooltip({ active, payload, label }) {
  const colors = useContext(DashboardThemeContext);
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: colors.surfaceLight, border: `1px solid ${colors.borderLight}`, borderRadius: 6, padding: "8px 12px", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>
      <div style={{ color: colors.textMuted, marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, display: "flex", gap: 8, justifyContent: "space-between" }}>
          <span>{p.name || p.dataKey}</span>
          <span style={{ fontWeight: 600 }}>{typeof p.value === 'number' ? p.value.toFixed(2) : p.value}</span>
        </div>
      ))}
    </div>
  );
}

export default CustomTooltip;
