import React, { useContext } from "react";
import { FaCaretUp, FaCaretDown } from "react-icons/fa";
import { DashboardThemeContext } from "../../theme";
import InfoBubble from "./InfoBubble";

function MetricCard({ label, value, unit, delta, description, color, info }) {
  const colors = useContext(DashboardThemeContext);
  const cardColor = color || colors.accent;
  return (
    <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 8, padding: "14px 16px", flex: 1, minWidth: 140 }}>
      <div style={{ fontSize: 10, color: colors.textDim, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6, fontFamily: "'JetBrains Mono', monospace", display: "flex", alignItems: "center", gap: 6 }}>
        {label}
        {info && <InfoBubble info={info} size={10} />}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
        <span style={{ fontSize: 24, fontWeight: 700, color: cardColor, fontFamily: "'JetBrains Mono', monospace" }}>{value}</span>
        {unit && <span style={{ fontSize: 12, color: colors.textMuted }}>{unit}</span>}
      </div>
      {delta !== undefined && (
        <div style={{ fontSize: 11, color: delta >= 0 ? colors.green : colors.red, marginTop: 4, fontFamily: "'JetBrains Mono', monospace" }}>
          {delta >= 0 ? <FaCaretUp size={10} style={{ display: "inline", verticalAlign: "middle" }} /> : <FaCaretDown size={10} style={{ display: "inline", verticalAlign: "middle" }} />} {Math.abs(delta).toFixed(1)}% vs benchmark
        </div>
      )}
      {description && <div style={{ fontSize: 10, color: colors.textDim, marginTop: 4 }}>{description}</div>}
    </div>
  );
}

export default React.memo(MetricCard);
