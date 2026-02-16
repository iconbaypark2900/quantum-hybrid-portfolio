import React, { useContext } from "react";
import { DashboardThemeContext } from "../../theme";

function TabButton({ active, onClick, children, icon }) {
  const colors = useContext(DashboardThemeContext);
  return (
    <button onClick={onClick} style={{
      padding: "10px 18px", background: active ? colors.accentGlow : "transparent",
      border: `1px solid ${active ? colors.accent : "transparent"}`, borderRadius: 6,
      color: active ? colors.accent : colors.textMuted, fontSize: 13, fontWeight: active ? 600 : 400,
      cursor: "pointer", transition: "all 0.2s", display: "flex", alignItems: "center", gap: 6,
      fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.02em",
    }}>
      {icon && <span style={{ fontSize: 15 }}>{icon}</span>}
      {children}
    </button>
  );
}

export default React.memo(TabButton);
