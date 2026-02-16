import React, { useContext } from "react";
import { DashboardThemeContext } from "../../theme";

function LoadingOverlay({ message = "Loading..." }) {
  const colors = useContext(DashboardThemeContext);
  return (
    <div style={{
      position: "absolute", inset: 0, background: `${colors.bg}CC`,
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      zIndex: 10, borderRadius: 10,
    }}>
      <div style={{
        width: 32, height: 32, border: `3px solid ${colors.border}`,
        borderTop: `3px solid ${colors.accent}`, borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
      }} />
      <div style={{ marginTop: 12, fontSize: 12, color: colors.textMuted, fontFamily: "'JetBrains Mono', monospace" }}>{message}</div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

export default LoadingOverlay;
