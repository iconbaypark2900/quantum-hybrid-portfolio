import React, { useState, useContext } from "react";
import { FaChevronRight } from "react-icons/fa";
import { DashboardThemeContext } from "../../theme";

function CollapsibleSection({ title, defaultOpen = true, children }) {
  const colors = useContext(DashboardThemeContext);
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ marginBottom: 4 }}>
      <button onClick={() => setOpen(!open)} style={{
        display: "flex", alignItems: "center", gap: 6, width: "100%", padding: "6px 0", background: "transparent",
        border: "none", cursor: "pointer", fontSize: 10, fontWeight: 600, color: colors.textDim,
        textTransform: "uppercase", letterSpacing: "0.1em", fontFamily: "'JetBrains Mono', monospace"
      }}>
        <FaChevronRight size={10} style={{ transition: "transform 0.2s", transform: open ? "rotate(90deg)" : "rotate(0)", flexShrink: 0 }} />
        {title}
      </button>
      {open && <div style={{ paddingTop: 8 }}>{children}</div>}
    </div>
  );
}

export default CollapsibleSection;
