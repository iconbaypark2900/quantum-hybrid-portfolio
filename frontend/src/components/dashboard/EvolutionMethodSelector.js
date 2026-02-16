import React, { useContext } from "react";
import { FaCircle, FaRegCircle, FaAdjust, FaBolt, FaWaveSquare } from "react-icons/fa";
import { DashboardThemeContext } from "../../theme";

function EvolutionMethodSelector({ value, onChange }) {
  const colors = useContext(DashboardThemeContext);
  const methods = [
    { key: "continuous", label: "Continuous", icon: <FaCircle size={14} />, color: colors.accent },
    { key: "discrete", label: "Discrete", icon: <FaRegCircle size={14} />, color: colors.purple },
    { key: "decoherent", label: "Decoherent", icon: <FaAdjust size={14} />, color: colors.cyan },
    { key: "adiabatic", label: "Adiabatic", icon: <FaBolt size={14} />, color: colors.pink },
    { key: "variational", label: "Variational", icon: <FaWaveSquare size={14} />, color: colors.orange },
  ];
  return (
    <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
      {methods.map(m => (
        <button key={m.key} onClick={() => onChange(m.key)} style={{
          flex: 1, padding: "8px 4px", background: value === m.key ? `${m.color}18` : "transparent",
          border: `1px solid ${value === m.key ? m.color : colors.border}`, borderRadius: 6,
          color: value === m.key ? m.color : colors.textDim, fontSize: 11, cursor: "pointer",
          fontFamily: "'JetBrains Mono', monospace", transition: "all 0.2s", textAlign: "center"
        }}>
          <div style={{ fontSize: 16 }}>{m.icon}</div>
          <div style={{ marginTop: 2 }}>{m.label}</div>
        </button>
      ))}
    </div>
  );
}

export default React.memo(EvolutionMethodSelector);
