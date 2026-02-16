import React, { useContext } from "react";
import { DashboardThemeContext } from "../../theme";

function ConfirmDialog({ title, message, onConfirm, onCancel }) {
  const colors = useContext(DashboardThemeContext);
  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }} onClick={onCancel}>
      <div
        style={{
          background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 12,
          padding: 24, width: 380, maxWidth: "90vw",
        }}
        onClick={e => e.stopPropagation()}
      >
        <h3 style={{ margin: "0 0 8px 0", fontSize: 16, color: colors.text }}>{title}</h3>
        <p style={{ margin: "0 0 20px 0", fontSize: 13, color: colors.textMuted, lineHeight: 1.5 }}>{message}</p>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <button
            onClick={onCancel}
            style={{
              padding: "8px 18px", background: "transparent", border: `1px solid ${colors.border}`,
              borderRadius: 6, color: colors.textMuted, cursor: "pointer", fontSize: 13,
            }}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            style={{
              padding: "8px 18px", background: colors.accent, border: "none",
              borderRadius: 6, color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600,
            }}
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmDialog;
