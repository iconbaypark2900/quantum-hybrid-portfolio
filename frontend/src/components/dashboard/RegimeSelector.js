import React, { useContext } from "react";
import { FaDotCircle, FaCaretUp, FaCaretDown, FaChartLine } from "react-icons/fa";
import { DashboardThemeContext } from "../../theme";

function RegimeSelector({ value, onChange }) {
  const colors = useContext(DashboardThemeContext);
  const regimes = [
    { key: "normal", label: "Normal", icon: <FaDotCircle size={14} />, color: colors.accent },
    { key: "bull", label: "Bull", icon: <FaCaretUp size={14} />, color: colors.green },
    { key: "bear", label: "Bear", icon: <FaCaretDown size={14} />, color: colors.red },
    { key: "volatile", label: "Volatile", icon: <FaChartLine size={14} />, color: colors.orange },
  ];
  return (
    <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
      {regimes.map(r => (
        <button key={r.key} onClick={() => onChange(r.key)} style={{
          flex: 1, padding: "8px 4px", background: value === r.key ? `${r.color}18` : "transparent",
          border: `1px solid ${value === r.key ? r.color : colors.border}`, borderRadius: 6,
          color: value === r.key ? r.color : colors.textDim, fontSize: 11, cursor: "pointer",
          fontFamily: "'JetBrains Mono', monospace", transition: "all 0.2s", textAlign: "center"
        }}>
          <div style={{ fontSize: 16 }}>{r.icon}</div>
          <div style={{ marginTop: 2 }}>{r.label}</div>
        </button>
      ))}
    </div>
  );
}

export default React.memo(RegimeSelector);
