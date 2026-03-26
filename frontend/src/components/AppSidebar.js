import React, { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  FaFlask,
  FaChartLine,
  FaShieldAlt,
  FaLayerGroup,
  FaCog,
  FaAtom,
} from "react-icons/fa";

const NAV_ITEMS = [
  { to: "/", icon: <FaFlask />, label: "Portfolio Lab", exact: true },
  { to: "/backtest", icon: <FaChartLine />, label: "Backtest" },
  { to: "/risk", icon: <FaShieldAlt />, label: "Risk Analysis" },
  { to: "/scenarios", icon: <FaLayerGroup />, label: "Scenarios" },
  { to: "/settings", icon: <FaCog />, label: "Settings" },
];

const SIDEBAR_W = 64;

export default function AppSidebar() {
  const location = useLocation();
  const [hovered, setHovered] = useState(null);

  return (
    <nav
      style={{
        width: SIDEBAR_W,
        minWidth: SIDEBAR_W,
        height: "100vh",
        background: "#070B14",
        borderRight: "1px solid #1E293B",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        paddingTop: 16,
        paddingBottom: 16,
        position: "fixed",
        top: 0,
        left: 0,
        zIndex: 200,
      }}
    >
      {/* Logo */}
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: 10,
          background: "linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: 28,
          fontSize: 18,
          color: "#fff",
          flexShrink: 0,
        }}
      >
        <FaAtom />
      </div>

      {/* Nav items */}
      <div style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1, width: "100%" }}>
        {NAV_ITEMS.map((item) => {
          const isActive = item.exact
            ? location.pathname === item.to
            : location.pathname.startsWith(item.to);

          return (
            <div key={item.to} style={{ position: "relative" }}>
              <NavLink
                to={item.to}
                onMouseEnter={() => setHovered(item.to)}
                onMouseLeave={() => setHovered(null)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "100%",
                  height: 44,
                  fontSize: 18,
                  color: isActive ? "#3B82F6" : "#4A5578",
                  background: isActive ? "rgba(59,130,246,0.12)" : "transparent",
                  borderLeft: isActive ? "3px solid #3B82F6" : "3px solid transparent",
                  transition: "all 0.15s",
                  textDecoration: "none",
                  cursor: "pointer",
                }}
              >
                {item.icon}
              </NavLink>

              {/* Tooltip */}
              {hovered === item.to && (
                <div
                  style={{
                    position: "absolute",
                    left: SIDEBAR_W + 8,
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "#1A2235",
                    border: "1px solid #2D3A52",
                    color: "#E2E8F0",
                    fontSize: 12,
                    fontWeight: 500,
                    padding: "5px 10px",
                    borderRadius: 6,
                    whiteSpace: "nowrap",
                    pointerEvents: "none",
                    zIndex: 300,
                  }}
                >
                  {item.label}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </nav>
  );
}
