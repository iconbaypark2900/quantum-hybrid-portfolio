import React, { useState, useContext } from "react";
import { FaInfoCircle } from "react-icons/fa";
import { DashboardThemeContext } from "../../theme";

/**
 * Informational bubble: small info icon that shows a tooltip on hover/focus.
 * @param {string} info - Help text to display in the tooltip
 * @param {number} size - Icon size in px (default 12)
 * @param {string} placement - "top" | "bottom" | "left" | "right" (default "top")
 * @param {number} maxWidth - Max tooltip width in px (default 240)
 */
function InfoBubble({ info, size = 12, placement = "top", maxWidth = 240 }) {
  const colors = useContext(DashboardThemeContext);
  const [visible, setVisible] = useState(false);

  if (!info) return null;

  const positionStyles = {
    top: { bottom: "100%", left: "50%", transform: "translateX(-50%) translateY(-6px)", marginBottom: 4 },
    bottom: { top: "100%", left: "50%", transform: "translateX(-50%) translateY(6px)", marginTop: 4 },
    left: { right: "100%", top: "50%", transform: "translateY(-50%) translateX(-6px)", marginRight: 4 },
    right: { left: "100%", top: "50%", transform: "translateY(-50%) translateX(6px)", marginLeft: 4 },
  };
  const pos = positionStyles[placement] || positionStyles.top;

  return (
    <span
      style={{ position: "relative", display: "inline-flex", alignItems: "center", cursor: "help" }}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
      role="img"
      aria-label={info}
      tabIndex={0}
    >
      <FaInfoCircle
        size={size}
        style={{ color: colors.textDim, opacity: 0.8, flexShrink: 0 }}
        aria-hidden
      />
      {visible && (
        <span
          role="tooltip"
          style={{
            position: "absolute",
            ...pos,
            zIndex: 1000,
            maxWidth,
            padding: "8px 12px",
            background: colors.surface,
            border: `1px solid ${colors.border}`,
            borderRadius: 8,
            fontSize: 11,
            color: colors.text,
            lineHeight: 1.5,
            fontFamily: "'JetBrains Mono', monospace",
            boxShadow: "0 4px 12px rgba(0,0,0,0.25)",
            pointerEvents: "none",
          }}
        >
          {info}
        </span>
      )}
    </span>
  );
}

export default React.memo(InfoBubble);
