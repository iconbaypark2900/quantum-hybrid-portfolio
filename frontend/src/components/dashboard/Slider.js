import React, { useContext } from "react";
import { DashboardThemeContext } from "../../theme";
import InfoBubble from "./InfoBubble";

function Slider({ label, value, onChange, min, max, step, unit = "", info, customLabel, customColor }) {
  const colors = useContext(DashboardThemeContext);
  const id = `slider-${label.replace(/\s+/g, '-').toLowerCase()}`;
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
        <label htmlFor={id} style={{ fontSize: 12, color: customColor || colors.textMuted, letterSpacing: "0.05em", textTransform: "uppercase", fontFamily: "'JetBrains Mono', monospace", cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
          {customLabel || label}
          {info && <InfoBubble info={info} size={11} />}
        </label>
        <span style={{ fontSize: 13, color: customColor || colors.accent, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>
          {typeof value === 'number' ? value.toFixed(step < 1 ? 2 : 0) : value}{unit}
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        aria-label={customLabel || label}
        aria-valuenow={value}
        aria-valuemin={min}
        aria-valuemax={max}
        style={{
          width: "100%", height: 8, appearance: "none",
          background: `linear-gradient(to right, ${customColor || colors.accent} ${((value - min) / (max - min)) * 100}%, ${colors.border} ${((value - min) / (max - min)) * 100}%)`,
          borderRadius: 4, outline: "none", cursor: "pointer", marginTop: 8
        }}
        onFocus={(e) => { e.target.style.boxShadow = `0 0 0 ${colors.focusOutlineWidth} ${colors.focusOutline}`; }}
        onBlur={(e) => { e.target.style.boxShadow = "none"; }}
      />
    </div>
  );
}

export default React.memo(Slider);
