import React, { useContext } from "react";
import { FaBalanceScale, FaSync, FaRocket, FaShieldAlt } from "react-icons/fa";
import { DashboardThemeContext } from "../../theme";

function ObjectiveSelector({ value, onChange }) {
  const colors = useContext(DashboardThemeContext);
  const objectives = [
    { key: "balanced", label: "Balanced", icon: <FaBalanceScale size={16} />, color: colors.accent },
    { key: "diversification", label: "Diversify", icon: <FaSync size={16} />, color: colors.green },
    { key: "momentum", label: "Momentum", icon: <FaRocket size={16} />, color: colors.orange },
    { key: "conservative", label: "Conserve", icon: <FaShieldAlt size={16} />, color: colors.red },
  ];
  return (
    <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
      {objectives.map(o => (
        <button key={o.key} onClick={() => onChange(o.key)} style={{
          flex: 1, padding: "8px 4px", background: value === o.key ? `${o.color}18` : "transparent",
          border: `1px solid ${value === o.key ? o.color : colors.border}`, borderRadius: 6,
          color: value === o.key ? o.color : colors.textDim, fontSize: 11, cursor: "pointer",
          fontFamily: "'JetBrains Mono', monospace", transition: "all 0.2s", textAlign: "center"
        }}>
          <div style={{ fontSize: 16 }}>{o.icon}</div>
          <div style={{ marginTop: 2 }}>{o.label}</div>
        </button>
      ))}
    </div>
  );
}

export default React.memo(ObjectiveSelector);
