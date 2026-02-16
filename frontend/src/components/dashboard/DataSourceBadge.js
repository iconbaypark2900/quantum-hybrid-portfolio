import React, { useContext } from "react";
import { DashboardThemeContext } from "../../theme";
import InfoBubble from "./InfoBubble";

function DataSourceBadge({ source }) {
  const colors = useContext(DashboardThemeContext);
  const isApi = source === "api";
  const badgeColor = isApi ? colors.green : colors.accent;
  const label = isApi ? "LIVE" : "SIM";
  const info = isApi
    ? "Using live API: optimizes with real market data and current covariance."
    : "Simulation mode: uses synthetic market data generated from regime parameters.";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span style={{ padding: "3px 8px", color: badgeColor, background: `${badgeColor}18`, border: `1px solid ${badgeColor}40`, letterSpacing: "0.05em", fontSize: 11, fontFamily: "'JetBrains Mono', monospace", borderRadius: 4 }}>
        {label}
      </span>
      <InfoBubble info={info} size={11} />
    </span>
  );
}

export default React.memo(DataSourceBadge);
