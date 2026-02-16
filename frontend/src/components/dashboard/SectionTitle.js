import React, { useContext } from "react";
import { DashboardThemeContext } from "../../theme";
import InfoBubble from "./InfoBubble";

function SectionTitle({ children, subtitle, info }) {
  const colors = useContext(DashboardThemeContext);
  return (
    <div style={{ marginBottom: 16 }}>
      <h3 style={{ fontSize: 15, fontWeight: 700, color: colors.text, margin: 0, fontFamily: "'Space Grotesk', sans-serif", letterSpacing: "-0.01em", display: "flex", alignItems: "center", gap: 8 }}>
        {children}
        {info && <InfoBubble info={info} size={12} />}
      </h3>
      {subtitle && <p style={{ fontSize: 11, color: colors.textDim, margin: "4px 0 0 0" }}>{subtitle}</p>}
    </div>
  );
}

export default React.memo(SectionTitle);
