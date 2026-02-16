import React, { useContext } from "react";
import InfoBubble from "./InfoBubble";
import { DashboardThemeContext } from "../../theme";

/**
 * Section label with optional info bubble (for left panel section headers).
 */
function SectionLabel({ title, info }) {
  const colors = useContext(DashboardThemeContext);
  return (
    <div style={{ fontSize: 10, color: colors.textDim, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12, fontFamily: "'JetBrains Mono', monospace", display: "flex", alignItems: "center", gap: 6 }}>
      {title}
      {info && <InfoBubble info={info} size={10} />}
    </div>
  );
}

export default React.memo(SectionLabel);
